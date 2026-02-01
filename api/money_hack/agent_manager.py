import base64
from datetime import UTC
from datetime import datetime

from core.exceptions import UnauthorizedException
from core.requester import Requester
from core.util import chain_util
from core.web3.eth_client import ABI
from core.web3.eth_client import RestEthClient
from eth_account.messages import _hash_eip191_message
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3 import Web3

from money_hack.api.authorizer import Authorizer
from money_hack.api.v1_resources import AuthToken
from money_hack.api.v1_resources import CollateralAsset
from money_hack.api.v1_resources import Position
from money_hack.api.v1_resources import UserConfig

w3 = Web3()

ERC1271_ABI: ABI = [
    {
        'inputs': [{'name': '_hash', 'type': 'bytes32'}, {'name': '_signature', 'type': 'bytes'}],
        'name': 'isValidSignature',
        'outputs': [{'name': '', 'type': 'bytes4'}],
        'type': 'function',
    },
]

SUPPORTED_COLLATERALS = [
    CollateralAsset(chain_id=8453, address='0x4200000000000000000000000000000000000006', symbol='WETH', name='Wrapped Ether', decimals=18, logo_uri='https://assets.coingecko.com/coins/images/2518/small/weth.png'),
    CollateralAsset(chain_id=8453, address='0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', symbol='WBTC', name='Wrapped Bitcoin', decimals=8, logo_uri='https://assets.coingecko.com/coins/images/7598/small/wrapped_bitcoin_wbtc.png'),
    CollateralAsset(chain_id=8453, address='0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf', symbol='cbBTC', name='Coinbase Wrapped BTC', decimals=8, logo_uri='https://assets.coingecko.com/coins/images/40143/standard/cbbtc.webp'),
]


class AgentManager(Authorizer):
    def __init__(
        self,
        requester: Requester,
        chainId: int,
        ethClient: RestEthClient,
    ) -> None:
        self.chainId = chainId
        self.requester = requester
        self.ethClient = ethClient
        self._signatureSignerMap: dict[str, str] = {}

    async def _retrieve_signature_signer_address(self, signatureString: str) -> str:
        if signatureString in self._signatureSignerMap:
            return self._signatureSignerMap[signatureString]
        authTokenJson = base64.b64decode(signatureString).decode('utf-8')
        authToken = AuthToken.model_validate_json(authTokenJson)
        messageHash = encode_defunct(text=authToken.message)
        isSmartWallet = len(authToken.signature) != 132  # noqa: PLR2004
        siweMessage = SiweMessage.from_message(message=authToken.message)
        signerId = chain_util.normalize_address(siweMessage.address)
        if isSmartWallet:
            prefixedMessageHash = '0x' + HexBytes(_hash_eip191_message(messageHash)).hex()
            response = await self.ethClient.call_function_by_name(
                toAddress=signerId,
                contractAbi=ERC1271_ABI,
                functionName='isValidSignature',
                arguments={'_hash': prefixedMessageHash, '_signature': authToken.signature},
            )
            responseValue = '0x' + response[0].hex()
            if responseValue != '0x1626ba7e':
                raise UnauthorizedException
        else:
            messageSignerId = chain_util.normalize_address(w3.eth.account.recover_message(messageHash, signature=authToken.signature))
            if messageSignerId != signerId:
                raise UnauthorizedException
        self._signatureSignerMap[signatureString] = signerId
        return signerId

    async def retrieve_signature_signer(self, signatureString: str) -> str:
        signerAddress = await self._retrieve_signature_signer_address(signatureString=signatureString)
        return signerAddress

    async def get_supported_collaterals(self) -> list[CollateralAsset]:
        return SUPPORTED_COLLATERALS

    async def get_user_config(self, user_address: str) -> UserConfig:  # noqa: ARG002
        return UserConfig(telegram_handle=None, preferred_ltv=0.75)

    async def update_user_config(self, user_address: str, telegram_handle: str | None, preferred_ltv: float) -> UserConfig:  # noqa: ARG002
        return UserConfig(telegram_handle=telegram_handle, preferred_ltv=preferred_ltv)

    async def create_position(self, user_address: str, collateral_asset_address: str, collateral_amount: str, target_ltv: float) -> Position:
        collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == collateral_asset_address.lower()), SUPPORTED_COLLATERALS[0])
        collateral_value = 100000.0
        borrow_value = collateral_value * target_ltv
        return Position(
            position_id=f'pos-{user_address[:8]}',
            created_date=datetime.now(tz=UTC),
            user_address=user_address,
            collateral_asset=collateral,
            collateral_amount=collateral_amount,
            collateral_value_usd=collateral_value,
            borrow_amount=str(int(borrow_value * 1e6)),
            borrow_value_usd=borrow_value,
            current_ltv=target_ltv,
            target_ltv=target_ltv,
            health_factor=1.0 / target_ltv,
            vault_balance=str(int(borrow_value * 1e6)),
            vault_balance_usd=borrow_value,
            accrued_yield='0',
            accrued_yield_usd=0.0,
            estimated_apy=0.08,
            status='active',
        )

    async def get_position(self, user_address: str) -> Position | None:  # noqa: ARG002
        return None

    async def withdraw_usdc(self, user_address: str, amount: str) -> tuple[Position, str]:
        raise NotImplementedError('withdraw_usdc not implemented')

    async def close_position(self, user_address: str) -> str:  # noqa: ARG002
        return '0x' + '0' * 64
