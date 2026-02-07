import asyncio
import typing

from core.exceptions import BadRequestException
from core.exceptions import KibaException
from core.util.typing_util import JsonObject
from core.web3.eth_client import EncodedCall
from core.web3.eth_client import RestEthClient

from money_hack.smart_wallets.coinbase_constants import COINBASE_ENTRYPOINT_ABI
from money_hack.smart_wallets.coinbase_constants import COINBASE_ENTRYPOINT_ADDRESS
from money_hack.smart_wallets.model import Bundler
from money_hack.smart_wallets.model import UserOperation
from money_hack.smart_wallets.model import UserOperationFailedException
from money_hack.smart_wallets.model import UserOperationReceipt

WHITELISTED_ADDRESSES = {
    # General
    '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # USDC Base Mainnet
    '0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789',  # Entrypoint v06
    # Tokens
    '0x4200000000000000000000000000000000000006',  # WETH
    '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf',  # cbBTC
    # Morpho Blue
    '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb',  # Morpho Blue
    # Vaults
    '0x0000000f2eB9f69274678c76222B35eEc7588a65',  # Yo USDC Vault (40acres)
    # ENS (mainnet)
    '0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63',  # ENS Public Resolver (text records + multicall)
    '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e',  # ENS Registry (subname registration)
    # LI.FI
    '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',  # LI.FI Diamond Proxy (cross-chain bridge router)
}


class GasCostTooHighException(KibaException):
    def __init__(self, message: str | None = None) -> None:
        message = message if message else 'SPONSORED_GAS_COSTS_TOO_HIGH'
        super().__init__(message=message)


class CoinbaseBundler(Bundler):
    def __init__(self, paymasterEthClient: RestEthClient) -> None:
        self.paymasterEthClient = paymasterEthClient

    async def _get_entry_point_nonce(self, sender: str, nonceKey: int = 0) -> int:
        response = await self.paymasterEthClient.call_function_by_name(
            toAddress=COINBASE_ENTRYPOINT_ADDRESS,
            contractAbi=COINBASE_ENTRYPOINT_ABI,
            functionName='getNonce',
            arguments={'sender': sender, 'key': nonceKey},
        )
        return int(response[0])

    async def prepare_user_operation_for_signing(self, sender: str, callData: str) -> UserOperation:
        entryPointNonce = await self._get_entry_point_nonce(sender=sender)
        return {
            'sender': sender,
            'nonce': hex(entryPointNonce),
            'initCode': '0x',
            'callData': callData,
            'callGasLimit': hex(0),
            'verificationGasLimit': hex(0),
            'preVerificationGas': hex(0),
            'maxFeePerGas': hex(0),
            'maxPriorityFeePerGas': hex(0),
            'paymasterAndData': '0x',
            'signature': '0x' + '0' * 130,
        }

    async def build_user_operation(
        self,
        chainId: int,
        sender: str,
        callData: str,
        shouldSponsorGas: bool = False,
        context: JsonObject | None = None,
        presignedSignature: str | None = None,
    ) -> UserOperation:
        userOperation = await self.prepare_user_operation_for_signing(sender=sender, callData=callData)
        if presignedSignature:
            userOperation['signature'] = presignedSignature
        if shouldSponsorGas:
            paymasterStubResponse = await self.paymasterEthClient._make_request(  # noqa: SLF001
                method='pm_getPaymasterStubData',
                params=[userOperation, COINBASE_ENTRYPOINT_ADDRESS, hex(chainId), context or {}],
            )
            userOperation['paymasterAndData'] = paymasterStubResponse['result']['paymasterAndData']
        userOperationGasEstimateResponse = await self.paymasterEthClient._make_request(  # noqa: SLF001
            method='eth_estimateUserOperationGas',
            params=[userOperation, COINBASE_ENTRYPOINT_ADDRESS],
        )
        userOperation['callGasLimit'] = hex(int(userOperationGasEstimateResponse['result']['callGasLimit'], 16))
        userOperation['verificationGasLimit'] = hex(int(userOperationGasEstimateResponse['result']['verificationGasLimit'], 16))
        userOperation['preVerificationGas'] = hex(int(userOperationGasEstimateResponse['result']['preVerificationGas'], 16))
        maxPriorityFeePerGas = await self.paymasterEthClient.get_max_priority_fee_per_gas()
        maxFeePerGas = await self.paymasterEthClient.get_max_fee_per_gas(maxPriorityFeePerGas=maxPriorityFeePerGas)
        userOperation['maxFeePerGas'] = hex(int(maxFeePerGas * 1.5))
        userOperation['maxPriorityFeePerGas'] = hex(int(maxPriorityFeePerGas * 1.1))
        if shouldSponsorGas:
            try:
                paymasterDataResponse = await self.paymasterEthClient._make_request(  # noqa: SLF001
                    method='pm_getPaymasterData',
                    params=[userOperation, COINBASE_ENTRYPOINT_ADDRESS, hex(chainId), context or {}],
                )
                userOperation['paymasterAndData'] = paymasterDataResponse['result']['paymasterAndData']
            except BadRequestException as exception:
                if exception.message and 'max sponsorship cost per user op exceeded' in exception.message:
                    raise GasCostTooHighException from exception
                raise
        return userOperation

    async def generate_user_operation_hash(self, userOperation: UserOperation) -> str:
        userOperationHashResponse = await self.paymasterEthClient.call_function_by_name(
            toAddress=COINBASE_ENTRYPOINT_ADDRESS,
            contractAbi=COINBASE_ENTRYPOINT_ABI,
            functionName='getUserOpHash',
            arguments={'userOp': userOperation},
        )
        userOperationHash = '0x' + typing.cast(str, userOperationHashResponse[0].hex())
        return userOperationHash

    async def send_user_operation(self, userOperation: UserOperation, signature: str | None = None) -> str:
        if signature is not None:
            userOperation['signature'] = signature
        sendUserOperationResponse = await self.paymasterEthClient._make_request(  # noqa: SLF001
            method='eth_sendUserOperation',
            params=[userOperation, COINBASE_ENTRYPOINT_ADDRESS],
        )
        userOperationHash = typing.cast(str, sendUserOperationResponse['result'])
        return userOperationHash

    async def get_user_operation_receipt(self, userOperationHash: str) -> UserOperationReceipt | None:
        response = await self.paymasterEthClient._make_request(  # noqa: SLF001
            method='eth_getUserOperationReceipt',
            params=[userOperationHash],
        )
        if response['result'] is None:
            return None
        receipt = typing.cast(UserOperationReceipt, response['result'])
        return receipt

    async def wait_for_user_operation_receipt(
        self,
        userOperationHash: str,
        sleepSeconds: int = 2,
        maxWaitSeconds: int = 120,
        raiseOnFailure: bool = True,
    ) -> UserOperationReceipt:
        startTime = asyncio.get_event_loop().time()
        while True:
            receipt = await self.get_user_operation_receipt(userOperationHash=userOperationHash)
            if receipt is not None:
                break
            currentTime = asyncio.get_event_loop().time()
            if currentTime - startTime >= maxWaitSeconds:
                raise TimeoutError(f'Transaction receipt not found after {maxWaitSeconds} seconds for userOperationHash: {userOperationHash}')
            await asyncio.sleep(sleepSeconds)
        if raiseOnFailure and not receipt.get('success'):
            raise UserOperationFailedException(receipt=receipt)
        return receipt

    def validate_calls(self, calls: list[EncodedCall], chainId: int) -> None:  # noqa: ARG002
        for call in calls:
            if call.toAddress not in WHITELISTED_ADDRESSES:
                raise KibaException(f'Call to {call.toAddress} is not whitelisted for user operations')
