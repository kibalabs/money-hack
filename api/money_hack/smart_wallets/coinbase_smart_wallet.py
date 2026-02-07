import typing

from core.exceptions import KibaException
from core.util import chain_util
from core.web3.eth_client import EncodedCall
from core.web3.eth_client import RestEthClient
from eth_abi import encode
from eth_account.datastructures import SignedSetCodeAuthorization
from eth_account.typed_transactions.set_code_transaction import Authorization
from eth_keys.datatypes import Signature
from eth_typing import HexStr
from eth_utils import keccak
from eth_utils import to_canonical_address
from hexbytes import HexBytes
from pydantic import BaseModel
from web3._utils import method_formatters
from web3._utils.rpc_abi import RPC
from web3.types import TxParams
from web3.types import Wei

from money_hack.smart_wallets.coinbase_constants import COINBASE_EIP7702PROXY_ADDRESS
from money_hack.smart_wallets.coinbase_constants import COINBASE_EIP7702PROXY_EXPECTED_BYTECODE
from money_hack.smart_wallets.coinbase_constants import COINBASE_EIP7702PROXY_IMPLEMENTATION_SET_TYPEHASH
from money_hack.smart_wallets.coinbase_constants import COINBASE_ERC1967_IMPLEMENTATION_SLOT
from money_hack.smart_wallets.coinbase_constants import COINBASE_NONCE_TRACKER_ABI
from money_hack.smart_wallets.coinbase_constants import COINBASE_NONCE_TRACKER_ADDRESS
from money_hack.smart_wallets.coinbase_constants import COINBASE_SMART_WALLET_ABI
from money_hack.smart_wallets.coinbase_constants import COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS
from money_hack.smart_wallets.coinbase_constants import COINBASE_SMART_WALLET_VALIDATOR_ADDRESS
from money_hack.smart_wallets.coinbase_constants import MAX_UINT256
from money_hack.smart_wallets.model import SmartWallet


class DelegationStatus(BaseModel):
    code: str | None = None
    implementationAddress: str | None = None
    isDelegatedToCoinbaseSmartWallet: bool


class CoinbaseSmartWallet(SmartWallet):
    def __init__(self, ethClient: RestEthClient) -> None:
        self.ethClient = ethClient

    async def _get_nonce_from_tracker(self, address: str) -> int:
        response = await self.ethClient.call_function_by_name(
            toAddress=COINBASE_NONCE_TRACKER_ADDRESS,
            contractAbi=COINBASE_NONCE_TRACKER_ABI,
            functionName='nonces',
            arguments={'account': address},
        )
        return int(response[0])

    async def get_eip7702_authorization_dict(self, address: str, isUserMakingTransaction: bool) -> dict[str, int | str]:
        nonce = await self.ethClient.get_transaction_count(address=address)
        authDict: dict[str, int | str] = {
            'chainId': self.ethClient.chainId,
            'address': COINBASE_EIP7702PROXY_ADDRESS,
            'nonce': nonce + (1 if isUserMakingTransaction else 0),
        }
        return authDict

    async def create_set_implementation_hash(
        self,
        address: str,
        callData: str,
        proxyAddress: str = COINBASE_EIP7702PROXY_ADDRESS,
        newImplementationAddress: str = COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS,
        currentImplementationAddress: str = chain_util.BURN_ADDRESS,
        walletValidatorAddress: str = COINBASE_SMART_WALLET_VALIDATOR_ADDRESS,
        expiry: int = MAX_UINT256,
    ) -> str:
        nonce = await self._get_nonce_from_tracker(address=address)
        callDataHash = keccak(hexstr=callData)
        typeHash = keccak(COINBASE_EIP7702PROXY_IMPLEMENTATION_SET_TYPEHASH.encode('utf-8'))
        encodedData = encode(
            [
                'bytes32',  # typeHash
                'uint256',  # chainId
                'address',  # proxy
                'uint256',  # nonce
                'address',  # currentImplementation
                'address',  # newImplementation
                'bytes32',  # keccak256(callData)
                'address',  # validator
                'uint256',  # expiry
            ],
            [
                typeHash,
                self.ethClient.chainId,
                chain_util.normalize_address(proxyAddress),
                nonce,
                chain_util.normalize_address(currentImplementationAddress),
                chain_util.normalize_address(newImplementationAddress),
                callDataHash,
                chain_util.normalize_address(walletValidatorAddress),
                expiry,
            ],
        )
        return '0x' + keccak(encodedData).hex()

    def encode_set_implementation_call(
        self,
        initArgs: str,
        signedSetImplementationHash: str,
        newImplementationAddress: str = COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS,
        walletValidatorAddress: str = COINBASE_SMART_WALLET_VALIDATOR_ADDRESS,
        expiry: int = MAX_UINT256,
    ) -> str:
        return chain_util.encode_transaction_data(
            functionAbi={
                'type': 'function',
                'name': 'setImplementation',
                'inputs': [
                    {'name': 'newImplementation', 'type': 'address'},
                    {'name': 'callData', 'type': 'bytes'},
                    {'name': 'validator', 'type': 'address'},
                    {'name': 'expiry', 'type': 'uint256'},
                    {'name': 'signature', 'type': 'bytes'},
                    {'name': 'allowCrossChainReplay', 'type': 'bool'},
                ],
                'outputs': [],
                'stateMutability': 'payable',
            },
            arguments={
                'newImplementation': newImplementationAddress,
                'callData': initArgs,
                'validator': walletValidatorAddress,
                'expiry': expiry,
                'signature': signedSetImplementationHash,
                'allowCrossChainReplay': False,
            },
        )

    def encode_initialize_call(self, owners: list[str]) -> str:
        encodedOwners = [encode(['address'], [chain_util.normalize_address(owner)]) for owner in owners]
        return chain_util.encode_transaction_data(
            functionAbi={
                'type': 'function',
                'name': 'initialize',
                'inputs': [{'type': 'bytes[]', 'name': 'owners'}],
                'outputs': [],
                'stateMutability': 'payable',
            },
            arguments={'owners': encodedOwners},
        )

    async def _get_implementation_address(self, address: str, blockNumber: int | None = None) -> str:
        response = await self.ethClient._make_request(  # noqa: SLF001
            method='eth_getStorageAt',
            params=[address, COINBASE_ERC1967_IMPLEMENTATION_SLOT, hex(blockNumber) if blockNumber is not None else 'latest'],
        )
        implementationSlot = '0x' + typing.cast(HexBytes, method_formatters.PYTHONIC_RESULT_FORMATTERS[RPC.eth_getStorageAt](response['result'])).hex()
        return chain_util.normalize_address(implementationSlot)

    async def get_eoa_delegation_status(self, address: str, blockNumber: int | None = None) -> DelegationStatus:
        response = await self.ethClient._make_request(  # noqa: SLF001
            method='eth_getCode',
            params=[address, hex(blockNumber) if blockNumber is not None else 'latest'],
        )
        code: str | None = '0x' + typing.cast(HexBytes, method_formatters.PYTHONIC_RESULT_FORMATTERS[RPC.eth_getCode](response['result'])).hex()
        if code == '0x':
            code = None
        implementationSlot = await self._get_implementation_address(address=address)
        return DelegationStatus(
            code=code,
            implementationAddress=implementationSlot,
            isDelegatedToCoinbaseSmartWallet=(code == COINBASE_EIP7702PROXY_EXPECTED_BYTECODE and implementationSlot == COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS),
        )

    async def build_unsigned_authorization(self, walletAddress: str, targetAddress: str, isUserMakingTransaction: bool) -> Authorization:
        authDict = await self.get_eip7702_authorization_dict(address=walletAddress, isUserMakingTransaction=isUserMakingTransaction)
        return Authorization(chainId=authDict['chainId'], address=to_canonical_address(chain_util.normalize_address(targetAddress)), nonce=authDict['nonce'])

    def build_signed_authorization(self, unsignedAuthorization: Authorization, authSignatureHex: str) -> SignedSetCodeAuthorization:
        signatureBytes = bytes.fromhex(authSignatureHex.removeprefix('0x'))
        r = signatureBytes[:32]
        s = signatureBytes[32:64]
        v = signatureBytes[64]
        v = v - 27 if v >= 27 else v  # noqa: PLR2004
        normalizedSignatureBytes = r + s + bytes([v])
        authSignature = Signature(signature_bytes=normalizedSignatureBytes)
        return SignedSetCodeAuthorization(
            chain_id=unsignedAuthorization.chainId,
            address=unsignedAuthorization.address,
            nonce=unsignedAuthorization.nonce,
            y_parity=authSignature.v,
            r=authSignature.r,
            s=authSignature.s,
            signature=authSignature,
            authorization_hash=unsignedAuthorization.hash(),
        )

    async def build_delegation_transaction_params(
        self,
        walletAddress: str,
        signedAuthorization: SignedSetCodeAuthorization,
        data: str | None = None,
    ) -> TxParams:
        maxPriorityFeePerGas = await self.ethClient.get_max_priority_fee_per_gas()
        maxFeePerGas = await self.ethClient.get_max_fee_per_gas(maxPriorityFeePerGas=maxPriorityFeePerGas)
        return {
            'chainId': self.ethClient.chainId,
            'to': walletAddress,
            'value': typing.cast(Wei, 0),
            'data': typing.cast(HexStr, data if data is not None else hex(0)),
            'authorizationList': [signedAuthorization],
            'gas': 1_000_000,
            'maxFeePerGas': hex(maxFeePerGas),
            'maxPriorityFeePerGas': hex(maxPriorityFeePerGas),
        }

    async def validate_calls(self, calls: list[EncodedCall], chainId: int) -> None:
        pass

    def encode_user_operation_signature(self, signature: str, ownerIndex: int = 0) -> str:
        return chain_util.encode_function_params(
            functionAbi={
                'type': 'function',
                'name': '',
                'inputs': [
                    {
                        'components': [
                            {
                                'name': 'ownerIndex',
                                'type': 'uint8',
                            },
                            {
                                'name': 'signatureData',
                                'type': 'bytes',
                            },
                        ],
                        'type': 'tuple',
                    }
                ],
            },
            arguments=[(ownerIndex, signature)],
        )

    async def build_execute_call_data(self, chainId: int, calls: list[EncodedCall]) -> str:  # noqa: ARG002
        if len(calls) == 0:
            raise KibaException('No calls provided for smart wallet execution')
        if len(calls) == 1:
            return chain_util.encode_transaction_data_by_name(
                contractAbi=COINBASE_SMART_WALLET_ABI,
                functionName='execute',
                arguments={'target': calls[0].toAddress, 'value': calls[0].value, 'data': calls[0].data},
            )
        return chain_util.encode_transaction_data_by_name(
            contractAbi=COINBASE_SMART_WALLET_ABI,
            functionName='executeBatch',
            arguments={'calls': [(call.toAddress, call.value, bytes.fromhex(call.data.removeprefix('0x'))) for call in calls]},
        )
