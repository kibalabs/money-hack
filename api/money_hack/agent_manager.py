import base64
from datetime import UTC
from datetime import datetime

from core import logging
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
from money_hack.api.v1_resources import AssetBalance
from money_hack.api.v1_resources import AuthToken
from money_hack.api.v1_resources import CollateralAsset
from money_hack.api.v1_resources import CollateralMarketData
from money_hack.api.v1_resources import Position
from money_hack.api.v1_resources import UserConfig
from money_hack.api.v1_resources import Wallet
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.yo.yo_client import YoClient

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
    CollateralAsset(chain_id=8453, address='0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf', symbol='cbBTC', name='Coinbase Wrapped BTC', decimals=8, logo_uri='https://assets.coingecko.com/coins/images/40143/standard/cbbtc.webp'),
]

YO_VAULT_ADDRESS = '0x0000000f2eB9f69274678c76222B35eEc7588a65'
YO_VAULT_NAME = 'Yo USDC Vault'


class AgentManager(Authorizer):
    def __init__(
        self,
        requester: Requester,
        chainId: int,
        ethClient: RestEthClient,
        moralisClient: MoralisClient,
        alchemyClient: AlchemyClient,
        morphoClient: MorphoClient,
        yoClient: YoClient,
    ) -> None:
        self.chainId = chainId
        self.requester = requester
        self.ethClient = ethClient
        self.moralisClient = moralisClient
        self.alchemyClient = alchemyClient
        self.morphoClient = morphoClient
        self.yoClient = yoClient
        self._signatureSignerMap: dict[str, str] = {}

    async def _get_asset_price(self, assetAddress: str) -> float:
        """Get the current USD price for an asset. Tries Alchemy first, falls back to Moralis."""
        try:
            priceData = await self.alchemyClient.get_asset_current_price(chainId=self.chainId, assetAddress=assetAddress)
            return priceData.priceUsd
        except Exception as e:
            logging.warning(f'Alchemy price fetch failed for {assetAddress}, trying Moralis: {e}')
            try:
                priceData = await self.moralisClient.get_asset_current_price(chainId=self.chainId, assetAddress=assetAddress)
                return priceData.priceUsd
            except Exception as e2:
                logging.error(f'Both Alchemy and Moralis price fetch failed for {assetAddress}: {e2}')
                raise

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

        # Get real price for the collateral asset
        try:
            price_usd = await self._get_asset_price(assetAddress=collateral_asset_address)
            # Convert collateral_amount (raw) to human readable using decimals
            collateral_amount_human = int(collateral_amount) / (10**collateral.decimals)
            collateral_value = collateral_amount_human * price_usd
            logging.info(f'Price for {collateral.symbol}: ${price_usd:.2f}, collateral value: ${collateral_value:.2f}')
        except Exception as e:
            logging.error(f'Failed to fetch price for {collateral_asset_address}, using fallback: {e}')
            # Fallback to hardcoded value if price fetch fails
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

    async def get_market_data(self) -> tuple[list[CollateralMarketData], float, str, str]:
        collateralMarkets: list[CollateralMarketData] = []
        for collateral in SUPPORTED_COLLATERALS:
            market = await self.morphoClient.get_market(
                chain_id=self.chainId,
                collateral_address=collateral.address,
                loan_address=None,
            )
            if market is None:
                raise ValueError(f'No Morpho market found for collateral {collateral.symbol} ({collateral.address})')
            collateralMarkets.append(
                CollateralMarketData(
                    collateral_address=collateral.address,
                    collateral_symbol=collateral.symbol,
                    borrow_apy=market.borrow_apy,
                    max_ltv=market.lltv,
                    market_id=market.unique_key,
                )
            )
        yieldApy = await self.yoClient.get_yield_apy(chainId=self.chainId)
        if yieldApy is None:
            raise ValueError('Failed to get Yo.xyz yield APY')
        return collateralMarkets, yieldApy, YO_VAULT_ADDRESS, YO_VAULT_NAME

    async def withdraw_usdc(self, user_address: str, amount: str) -> tuple[Position, str]:
        raise NotImplementedError('withdraw_usdc not implemented')

    async def close_position(self, user_address: str) -> str:  # noqa: ARG002
        return '0x' + '0' * 64

    async def get_wallet(self, wallet_address: str) -> Wallet:
        walletAddress = chain_util.normalize_address(wallet_address)
        clientAssetBalances = await self.moralisClient.get_wallet_asset_balances(chainId=self.chainId, walletAddress=walletAddress)
        supportedAddresses = {c.address.lower() for c in SUPPORTED_COLLATERALS}
        assetBalances: list[AssetBalance] = []
        for clientBalance in clientAssetBalances:
            if clientBalance.assetAddress.lower() not in supportedAddresses:
                continue
            collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == clientBalance.assetAddress.lower()), None)
            if collateral is None:
                continue
            try:
                priceUsd = await self._get_asset_price(assetAddress=clientBalance.assetAddress)
                balanceHuman = clientBalance.balance / (10**collateral.decimals)
                balanceUsd = balanceHuman * priceUsd
            except Exception:  # noqa: BLE001
                balanceUsd = 0.0
            assetBalances.append(
                AssetBalance(
                    asset_address=clientBalance.assetAddress,
                    asset_symbol=collateral.symbol,
                    asset_decimals=collateral.decimals,
                    balance=str(clientBalance.balance),
                    balance_usd=balanceUsd,
                )
            )
        return Wallet(wallet_address=walletAddress, asset_balances=assetBalances)
