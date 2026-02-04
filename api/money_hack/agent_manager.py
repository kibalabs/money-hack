import base64
import typing
import uuid
from datetime import UTC
from datetime import datetime

from core import logging
from core.exceptions import KibaException
from core.exceptions import NotFoundException
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
from web3.types import Nonce
from web3.types import TxParams
from web3.types import Wei

from money_hack import constants
from money_hack.api.authorizer import Authorizer
from money_hack.api.v1_resources import Agent as AgentResource
from money_hack.api.v1_resources import AssetBalance
from money_hack.api.v1_resources import AuthToken
from money_hack.api.v1_resources import ClosePositionTransactionsData
from money_hack.api.v1_resources import CollateralAsset
from money_hack.api.v1_resources import CollateralMarketData
from money_hack.api.v1_resources import Position
from money_hack.api.v1_resources import PositionTransactionsData
from money_hack.api.v1_resources import TransactionCall
from money_hack.api.v1_resources import UserConfig
from money_hack.api.v1_resources import Wallet
from money_hack.api.v1_resources import WithdrawTransactionsData
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.external.coinbase_cdp_client import CoinbaseCdpClient
from money_hack.external.ens_client import EnsAgentConfig
from money_hack.external.ens_client import EnsClient
from money_hack.external.telegram_client import TelegramClient
from money_hack.forty_acres.forty_acres_client import FortyAcresClient
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.morpho.transaction_builder import TransactionBuilder
from money_hack.smart_wallets.coinbase_bundler import CoinbaseBundler
from money_hack.smart_wallets.coinbase_smart_wallet import CoinbaseSmartWallet
from money_hack.store.database_store import DatabaseStore

JsonObject = dict[str, object]

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
        fortyAcresClient: FortyAcresClient,
        telegramClient: TelegramClient,
        ensClient: EnsClient,
        databaseStore: DatabaseStore,
        coinbaseCdpClient: CoinbaseCdpClient | None = None,
        coinbaseSmartWallet: CoinbaseSmartWallet | None = None,
        coinbaseBundler: CoinbaseBundler | None = None,
    ) -> None:
        self.chainId = chainId
        self.requester = requester
        self.ethClient = ethClient
        self.moralisClient = moralisClient
        self.alchemyClient = alchemyClient
        self.morphoClient = morphoClient
        self.fortyAcresClient = fortyAcresClient
        self.telegramClient = telegramClient
        self.ensClient = ensClient
        self.databaseStore = databaseStore
        self.coinbaseCdpClient = coinbaseCdpClient
        self.coinbaseSmartWallet = coinbaseSmartWallet
        self.coinbaseBundler = coinbaseBundler
        self._signatureSignerMap: dict[str, str] = {}
        self._positionsCache: dict[str, Position] = {}
        self._userConfigsCache: dict[str, UserConfig] = {}

    async def _get_asset_price(self, assetAddress: str) -> float:
        """Get the current USD price for an asset. Tries Alchemy first, falls back to Moralis."""
        try:
            priceData = await self.alchemyClient.get_asset_current_price(chainId=self.chainId, assetAddress=assetAddress)
        except Exception as e:  # noqa: BLE001
            logging.warning(f'Alchemy price fetch failed for {assetAddress}, trying Moralis: {e}')
            try:
                priceData = await self.moralisClient.get_asset_current_price(chainId=self.chainId, assetAddress=assetAddress)
            except Exception as e2:
                logging.error(f'Both Alchemy and Moralis price fetch failed for {assetAddress}: {e2}')
                raise
            else:
                return priceData.priceUsd
        else:
            return priceData.priceUsd

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

    async def get_user_config(self, user_address: str) -> UserConfig:
        normalized_address = chain_util.normalize_address(user_address)
        if normalized_address in self._userConfigsCache:
            return self._userConfigsCache[normalized_address]
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalized_address)
        if user is not None:
            config = UserConfig(telegram_handle=user.telegramUsername, telegram_chat_id=user.telegramChatId, preferred_ltv=0.75)
            self._userConfigsCache[normalized_address] = config
            return config
        return UserConfig(telegram_handle=None, telegram_chat_id=None, preferred_ltv=0.75)

    async def update_user_config(self, user_address: str, telegram_handle: str | None, preferred_ltv: float | None) -> UserConfig:
        normalized_address = chain_util.normalize_address(user_address)
        currentConfig = await self.get_user_config(user_address=normalized_address)
        user = await self.databaseStore.get_or_create_user_by_wallet(walletAddress=normalized_address)
        telegramChatId = str(currentConfig.telegram_chat_id) if currentConfig.telegram_chat_id is not None else None
        await self.databaseStore.update_user_telegram(
            userId=user.userId,
            telegramId=user.telegramId,
            telegramChatId=telegramChatId,
            telegramUsername=telegram_handle,
        )
        config = UserConfig(telegram_handle=telegram_handle, telegram_chat_id=currentConfig.telegram_chat_id, preferred_ltv=preferred_ltv)
        self._userConfigsCache[normalized_address] = config
        return config

    async def create_agent(self, user_address: str, name: str, emoji: str) -> AgentResource:
        if self.coinbaseCdpClient is None:
            raise KibaException('Coinbase CDP client not configured')
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_or_create_user_by_wallet(walletAddress=normalizedAddress)
        existingAgents = await self.databaseStore.get_agents_by_user(userId=user.userId)
        if existingAgents:
            raise KibaException('User already has an agent')
        agentId = str(uuid.uuid4())
        walletAddress = await self.coinbaseCdpClient.create_eoa(name=agentId)
        agent = await self.databaseStore.create_agent(userId=user.userId, name=name, emoji=emoji, walletAddress=walletAddress)
        return AgentResource(
            agent_id=agent.agentId,
            name=agent.name,
            emoji=agent.emoji,
            agent_index=agent.agentIndex,
            wallet_address=agent.walletAddress,
            ens_name=agent.ensName,
            created_date=agent.createdDate,
        )

    async def get_agent(self, user_address: str) -> AgentResource | None:
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            return None
        agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
        if not agents:
            return None
        agent = agents[0]
        return AgentResource(
            agent_id=agent.agentId,
            name=agent.name,
            emoji=agent.emoji,
            agent_index=agent.agentIndex,
            wallet_address=agent.walletAddress,
            ens_name=agent.ensName,
            created_date=agent.createdDate,
        )

    async def deploy_agent(self, user_address: str, agent_id: str, collateral_asset_address: str, collateral_amount: str, target_ltv: float) -> tuple[Position, str | None]:
        if self.coinbaseCdpClient is None:
            raise KibaException('Coinbase CDP client not configured')
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise KibaException('User not found')
        agent = await self.databaseStore.get_agent_by_id(agentId=agent_id)
        if agent is None or agent.userId != user.userId:
            raise KibaException('Agent not found')
        collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == collateral_asset_address.lower()), SUPPORTED_COLLATERALS[0])
        try:
            priceUsd = await self._get_asset_price(assetAddress=collateral_asset_address)
            collateralAmountHuman = int(collateral_amount) / (10**collateral.decimals)
            collateralValue = collateralAmountHuman * priceUsd
        except Exception:  # noqa: BLE001
            logging.exception(f'Failed to fetch price for {collateral_asset_address}')
            collateralValue = 100000.0
        borrowValue = collateralValue * target_ltv
        borrowAmountRaw = int(borrowValue * 1e6)
        vaultSharesRaw = borrowAmountRaw
        estimatedApy = 0.08
        try:
            yieldApy = await self.fortyAcresClient.get_yield_apy(chainId=self.chainId)
            if yieldApy is not None:
                estimatedApy = yieldApy
        except Exception:  # noqa: BLE001
            logging.exception('Failed to get yield APY for position')
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=collateral_asset_address)
        morphoMarketId = market.unique_key if market else ''
        await self.databaseStore.create_position(
            agentId=agent.agentId,
            collateralAsset=collateral_asset_address,
            collateralAmount=int(collateral_amount),
            borrowAmount=borrowAmountRaw,
            targetLtv=target_ltv,
            vaultShares=vaultSharesRaw,
            morphoMarketId=morphoMarketId,
        )
        transactionHash = await self._execute_agent_deploy_transactions(
            agentWalletAddress=agent.walletAddress,
            collateralAssetAddress=collateral_asset_address,
            collateralAmount=collateral_amount,
            targetLtv=target_ltv,
        )
        position = Position(
            position_id=f'pos-{normalizedAddress[:8]}',
            created_date=datetime.now(tz=UTC),
            user_address=normalizedAddress,
            collateral_asset=collateral,
            collateral_amount=collateral_amount,
            collateral_value_usd=collateralValue,
            borrow_amount=str(borrowAmountRaw),
            borrow_value_usd=borrowValue,
            current_ltv=target_ltv,
            target_ltv=target_ltv,
            health_factor=1.0 / target_ltv,
            vault_balance=str(borrowAmountRaw),
            vault_balance_usd=borrowValue,
            accrued_yield='0',
            accrued_yield_usd=0.0,
            estimated_apy=estimatedApy,
            status='active',
        )
        self._positionsCache[normalizedAddress] = position
        return position, transactionHash

    async def _execute_agent_deploy_transactions(self, agentWalletAddress: str, collateralAssetAddress: str, collateralAmount: str, targetLtv: float) -> str | None:
        if self.coinbaseCdpClient is None:
            return None
        transactionsData = await self._build_position_transactions(
            userAddress=agentWalletAddress,
            collateralAssetAddress=collateralAssetAddress,
            collateralAmount=collateralAmount,
            targetLtv=targetLtv,
        )
        lastTxHash = None
        for tx in transactionsData.transactions:
            nonce = await self.ethClient.get_transaction_count(address=agentWalletAddress)
            maxPriorityFeePerGas = await self.ethClient.get_max_priority_fee_per_gas()
            maxFeePerGas = await self.ethClient.get_max_fee_per_gas(maxPriorityFeePerGas=maxPriorityFeePerGas)
            txParams = await self.ethClient.fill_transaction_params(
                params={'to': tx.to, 'data': HexBytes(tx.data), 'value': Wei(int(tx.value or '0'))},
                fromAddress=agentWalletAddress,
                nonce=nonce,
                maxFeePerGas=int(maxFeePerGas * 1.5),
                maxPriorityFeePerGas=int(maxPriorityFeePerGas * 1.2),
                chainId=self.chainId,
            )

            def parse_hex_int(value: object) -> int:
                strValue = str(value)
                return int(strValue, 16) if strValue.startswith('0x') else int(strValue)

            txParamsForSigning: TxParams = {
                'chainId': parse_hex_int(txParams['chainId']),
                'nonce': Nonce(parse_hex_int(txParams['nonce'])),
                'to': Web3.to_checksum_address(typing.cast(str, txParams['to'])),
                'data': HexBytes(txParams['data']),
                'value': Wei(parse_hex_int(txParams['value'])),
                'gas': int(parse_hex_int(txParams['gas']) * 1.2),
                'maxFeePerGas': Wei(parse_hex_int(txParams['maxFeePerGas'])),
                'maxPriorityFeePerGas': Wei(parse_hex_int(txParams['maxPriorityFeePerGas'])),
            }
            signedTx = await self.coinbaseCdpClient.sign_transaction(walletAddress=agentWalletAddress, transactionDict=txParamsForSigning)
            lastTxHash = await self.ethClient.send_raw_transaction(transactionData=signedTx)
            logging.info(f'Agent executed transaction: {lastTxHash}')
        return lastTxHash

    async def _build_position_transactions(self, userAddress: str, collateralAssetAddress: str, collateralAmount: str, targetLtv: float) -> PositionTransactionsData:
        return await self.get_position_transactions(user_address=userAddress, collateral_asset_address=collateralAssetAddress, collateral_amount=collateralAmount, target_ltv=targetLtv)

    async def create_position(self, user_address: str, collateral_asset_address: str, collateral_amount: str, target_ltv: float, agent_name: str, agent_emoji: str) -> tuple[Position, AgentResource]:
        collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == collateral_asset_address.lower()), SUPPORTED_COLLATERALS[0])
        try:
            price_usd = await self._get_asset_price(assetAddress=collateral_asset_address)
            collateral_amount_human = int(collateral_amount) / (10**collateral.decimals)
            collateral_value = collateral_amount_human * price_usd
            logging.info(f'Price for {collateral.symbol}: ${price_usd:.2f}, collateral value: ${collateral_value:.2f}')
        except Exception:  # noqa: BLE001
            logging.exception(f'Failed to fetch price for {collateral_asset_address}, using fallback')
            collateral_value = 100000.0
        borrow_value = collateral_value * target_ltv
        normalized_address = chain_util.normalize_address(user_address)
        estimated_apy = 0.08
        try:
            yield_apy = await self.fortyAcresClient.get_yield_apy(chainId=self.chainId)
            if yield_apy is not None:
                estimated_apy = yield_apy
        except Exception:  # noqa: BLE001
            logging.exception('Failed to get yield APY for position')
        user = await self.databaseStore.get_or_create_user_by_wallet(walletAddress=normalized_address)
        agentId = str(uuid.uuid4())
        walletAddress = normalized_address
        if self.coinbaseCdpClient is not None:
            walletAddress = await self.coinbaseCdpClient.create_eoa(name=agentId)
        agent = await self.databaseStore.create_agent(userId=user.userId, name=agent_name, emoji=agent_emoji, walletAddress=walletAddress)
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=collateral_asset_address)
        morphoMarketId = market.unique_key if market else ''
        borrowAmountRaw = int(borrow_value * 1e6)
        vaultSharesRaw = borrowAmountRaw
        await self.databaseStore.create_position(
            agentId=agent.agentId,
            collateralAsset=collateral_asset_address,
            collateralAmount=int(collateral_amount),
            borrowAmount=borrowAmountRaw,
            targetLtv=target_ltv,
            vaultShares=vaultSharesRaw,
            morphoMarketId=morphoMarketId,
        )
        position = Position(
            position_id=f'pos-{user_address[:8]}',
            created_date=datetime.now(tz=UTC),
            user_address=normalized_address,
            collateral_asset=collateral,
            collateral_amount=collateral_amount,
            collateral_value_usd=collateral_value,
            borrow_amount=str(borrowAmountRaw),
            borrow_value_usd=borrow_value,
            current_ltv=target_ltv,
            target_ltv=target_ltv,
            health_factor=1.0 / target_ltv,
            vault_balance=str(borrowAmountRaw),
            vault_balance_usd=borrow_value,
            accrued_yield='0',
            accrued_yield_usd=0.0,
            estimated_apy=estimated_apy,
            status='active',
        )
        self._positionsCache[normalized_address] = position
        agentResource = AgentResource(
            agent_id=agent.agentId,
            name=agent.name,
            emoji=agent.emoji,
            agent_index=agent.agentIndex,
            wallet_address=agent.walletAddress,
            ens_name=agent.ensName,
            created_date=agent.createdDate,
        )
        logging.info(f'Created position for {normalized_address}: {position.position_id}, agent: {agent.name}')
        return position, agentResource

    async def get_position(self, user_address: str) -> Position | None:
        normalized_address = chain_util.normalize_address(user_address)
        position = self._positionsCache.get(normalized_address)
        if position is None:
            user = await self.databaseStore.get_user_by_wallet(walletAddress=normalized_address)
            if user is None:
                return None
            agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
            if not agents:
                return None
            agent = agents[0]
            dbPosition = await self.databaseStore.get_position_by_agent(agentId=agent.agentId)
            if dbPosition is None:
                return None
            collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == dbPosition.collateralAsset.lower()), SUPPORTED_COLLATERALS[0])
            collateralAmountHuman = dbPosition.collateralAmount / (10**collateral.decimals)
            borrowValueUsd = dbPosition.borrowAmount / 1e6
            try:
                priceUsd = await self._get_asset_price(assetAddress=dbPosition.collateralAsset)
                collateralValueUsd = collateralAmountHuman * priceUsd
            except Exception:  # noqa: BLE001
                collateralValueUsd = 100000.0
            estimatedApy = 0.08
            try:
                yieldApy = await self.fortyAcresClient.get_yield_apy(chainId=self.chainId)
                if yieldApy is not None:
                    estimatedApy = yieldApy
            except Exception:  # noqa: BLE001
                logging.debug('Failed to get yield APY, using default')
            position = Position(
                position_id=f'pos-{normalized_address[:8]}',
                created_date=dbPosition.createdDate,
                user_address=normalized_address,
                collateral_asset=collateral,
                collateral_amount=str(dbPosition.collateralAmount),
                collateral_value_usd=collateralValueUsd,
                borrow_amount=str(dbPosition.borrowAmount),
                borrow_value_usd=borrowValueUsd,
                current_ltv=borrowValueUsd / collateralValueUsd if collateralValueUsd > 0 else 0,
                target_ltv=dbPosition.targetLtv,
                health_factor=0.86 / (borrowValueUsd / collateralValueUsd) if collateralValueUsd > 0 else 999,
                vault_balance=str(dbPosition.vaultShares),
                vault_balance_usd=dbPosition.vaultShares / 1e6,
                accrued_yield='0',
                accrued_yield_usd=0.0,
                estimated_apy=estimatedApy,
                status=dbPosition.status,
            )
            self._positionsCache[normalized_address] = position
        try:
            priceUsd = await self._get_asset_price(assetAddress=position.collateral_asset.address)
            collateralAmountHuman = int(position.collateral_amount) / (10**position.collateral_asset.decimals)
            collateralValue = collateralAmountHuman * priceUsd
            borrowValue = position.borrow_value_usd
            currentLtv = borrowValue / collateralValue if collateralValue > 0 else 0
            market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=position.collateral_asset.address)
            maxLtv = market.lltv if market else 0.86
            updatedPosition = Position(
                position_id=position.position_id,
                created_date=position.created_date,
                user_address=position.user_address,
                collateral_asset=position.collateral_asset,
                collateral_amount=position.collateral_amount,
                collateral_value_usd=collateralValue,
                borrow_amount=position.borrow_amount,
                borrow_value_usd=borrowValue,
                current_ltv=currentLtv,
                target_ltv=position.target_ltv,
                health_factor=maxLtv / currentLtv if currentLtv > 0 else 999,
                vault_balance=position.vault_balance,
                vault_balance_usd=position.vault_balance_usd,
                accrued_yield=position.accrued_yield,
                accrued_yield_usd=position.accrued_yield_usd,
                estimated_apy=position.estimated_apy,
                status=position.status,
            )
        except Exception:  # noqa: BLE001
            logging.exception('Failed to refresh position data')
            return position
        else:
            self._positionsCache[normalized_address] = updatedPosition
            return updatedPosition

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
        yieldApy = await self.fortyAcresClient.get_yield_apy(chainId=self.chainId)
        if yieldApy is None:
            raise ValueError('Failed to get Yo.xyz yield APY')
        return collateralMarkets, yieldApy, YO_VAULT_ADDRESS, YO_VAULT_NAME

    async def get_withdraw_transactions(self, user_address: str, amount: str) -> WithdrawTransactionsData:
        """Build transactions for partial withdrawal from vault (keeps position open)."""
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise NotFoundException(message='User not found')
        agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
        if not agents:
            raise NotFoundException(message='No agents found')
        agent = agents[0]
        dbPosition = await self.databaseStore.get_position_by_agent(agentId=agent.agentId)
        if dbPosition is None:
            raise NotFoundException(message='No active position found')
        withdrawAmount = int(amount)
        if withdrawAmount > dbPosition.vaultShares:
            raise ValueError(f'Requested withdrawal {withdrawAmount} exceeds vault balance {dbPosition.vaultShares}')
        usdcAddress = constants.CHAIN_USDC_MAP.get(self.chainId)
        if usdcAddress is None:
            raise ValueError(f'USDC not supported on chain {self.chainId}')
        transactionBuilder = TransactionBuilder(chainId=self.chainId, usdcAddress=usdcAddress, yoVaultAddress=YO_VAULT_ADDRESS)
        transactions = transactionBuilder.build_withdraw_transactions(user_address=normalizedAddress, withdraw_amount=withdrawAmount)
        logging.info(f'Built withdraw transactions for {normalizedAddress}: {withdrawAmount} USDC')
        return WithdrawTransactionsData(transactions=transactions, withdraw_amount=str(withdrawAmount), vault_address=YO_VAULT_ADDRESS)

    async def get_close_position_transactions(self, user_address: str) -> ClosePositionTransactionsData:
        """Build transactions to fully close a position: withdraw from vault, repay debt, withdraw collateral."""
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise NotFoundException(message='User not found')
        agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
        if not agents:
            raise NotFoundException(message='No agents found')
        agent = agents[0]
        dbPosition = await self.databaseStore.get_position_by_agent(agentId=agent.agentId)
        if dbPosition is None:
            raise NotFoundException(message='No active position found')
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=dbPosition.collateralAsset)
        if market is None:
            raise ValueError(f'No Morpho market found for collateral {dbPosition.collateralAsset}')
        usdcAddress = constants.CHAIN_USDC_MAP.get(self.chainId)
        if usdcAddress is None:
            raise ValueError(f'USDC not supported on chain {self.chainId}')
        vaultWithdrawAmount = dbPosition.vaultShares
        repayAmount = dbPosition.borrowAmount
        collateralAmount = dbPosition.collateralAmount
        transactionBuilder = TransactionBuilder(chainId=self.chainId, usdcAddress=usdcAddress, yoVaultAddress=YO_VAULT_ADDRESS)
        transactions = transactionBuilder.build_close_position_transactions_from_market(
            user_address=normalizedAddress,
            collateral_address=dbPosition.collateralAsset,
            collateral_amount=collateralAmount,
            repay_amount=repayAmount,
            vault_withdraw_amount=vaultWithdrawAmount,
            market=market,
            needs_usdc_approval=True,
        )
        logging.info(f'Built close position transactions for {normalizedAddress}: vault_withdraw={vaultWithdrawAmount}, repay={repayAmount}, collateral={collateralAmount}')
        return ClosePositionTransactionsData(
            transactions=transactions,
            collateral_amount=str(collateralAmount),
            repay_amount=str(repayAmount),
            vault_withdraw_amount=str(vaultWithdrawAmount),
            morpho_address=transactionBuilder.morphoAddress,
            vault_address=YO_VAULT_ADDRESS,
        )

    async def get_wallet(self, wallet_address: str) -> Wallet:
        walletAddress = chain_util.normalize_address(wallet_address)
        clientAssetBalances = await self.alchemyClient.get_wallet_asset_balances(chainId=self.chainId, walletAddress=walletAddress)
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

    async def get_position_transactions(self, user_address: str, collateral_asset_address: str, collateral_amount: str, target_ltv: float) -> PositionTransactionsData:
        collateral = next((c for c in SUPPORTED_COLLATERALS if c.address.lower() == collateral_asset_address.lower()), None)
        if collateral is None:
            raise ValueError(f'Unsupported collateral asset: {collateral_asset_address}')
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=collateral_asset_address)
        if market is None:
            raise ValueError(f'No Morpho market found for collateral {collateral.symbol}')
        priceUsd = await self._get_asset_price(assetAddress=collateral_asset_address)
        collateralAmountHuman = int(collateral_amount) / (10**collateral.decimals)
        collateralValueUsd = collateralAmountHuman * priceUsd
        borrowValueUsd = collateralValueUsd * target_ltv
        borrowAmount = int(borrowValueUsd * 1e6)
        logging.info(f'Building position transactions: collateral={collateral.symbol}, amount={collateralAmountHuman}, value=${collateralValueUsd:.2f}, borrow=${borrowValueUsd:.2f}')
        usdcAddress = constants.CHAIN_USDC_MAP.get(self.chainId)
        if usdcAddress is None:
            raise ValueError(f'USDC not supported on chain {self.chainId}')
        transactionBuilder = TransactionBuilder(chainId=self.chainId, usdcAddress=usdcAddress, yoVaultAddress=YO_VAULT_ADDRESS)
        transactions = transactionBuilder.build_position_transactions_from_market(
            user_address=user_address,
            collateral_address=collateral_asset_address,
            collateral_amount=int(collateral_amount),
            borrow_amount=borrowAmount,
            market=market,
        )
        return PositionTransactionsData(
            transactions=transactions,
            morpho_address=transactionBuilder.morphoAddress,
            vault_address=transactionBuilder.yoVaultAddress,
            estimated_borrow_amount=str(borrowAmount),
            needs_approval=True,
        )

    async def get_telegram_login_url(self) -> str:
        botUsername = await self.telegramClient.get_bot_username()
        return botUsername

    async def telegram_secret_verify(self, user_address: str, telegramSecret: str) -> UserConfig:
        normalizedAddress = chain_util.normalize_address(user_address)
        loginResult = await self.telegramClient.verify_secret_code(walletAddress=normalizedAddress, secretCode=telegramSecret)
        user = await self.databaseStore.get_or_create_user_by_wallet(walletAddress=normalizedAddress)
        await self.databaseStore.update_user_telegram(
            userId=user.userId,
            telegramId=loginResult.telegramUsername,
            telegramChatId=loginResult.chatId,
            telegramUsername=loginResult.telegramUsername,
        )
        await self.telegramClient.send_message(
            chatId=loginResult.chatId,
            text=f'✅ Your Telegram account has been linked to wallet {normalizedAddress[:8]}...{normalizedAddress[-6:]}. You will now receive notifications about your BorrowBot positions.',
        )
        updatedConfig = UserConfig(telegram_handle=loginResult.telegramUsername, telegram_chat_id=loginResult.chatId, preferred_ltv=0.75)
        self._userConfigsCache[normalizedAddress] = updatedConfig
        return updatedConfig

    async def process_telegram_webhook(self, updateDict: JsonObject) -> None:
        messageDict = typing.cast(JsonObject | None, updateDict.get('message'))
        if messageDict is None:
            logging.warning('Invalid Telegram update format: no message found')
            return
        chatId = typing.cast(int | None, typing.cast(JsonObject, messageDict.get('chat', {})).get('id'))
        if chatId is None:
            logging.warning('Invalid Telegram update format: no chat_id found')
            return
        senderUsername = typing.cast(str | None, typing.cast(JsonObject, messageDict.get('from', {})).get('username'))
        if senderUsername is None:
            logging.warning('Telegram message does not have a username set. Cannot proceed.')
            await self.telegramClient.send_message(
                chatId=str(chatId),
                text='Please make sure you have a Telegram username set to use this bot. You can set one in your Telegram settings.',
            )
            return
        messageText = typing.cast(str | None, messageDict.get('text'))
        if messageText is None:
            logging.warning('Telegram message has no text content, skipping processing.')
            return
        try:
            user = await self.databaseStore.get_user_by_telegram_id(telegramId=senderUsername)
            if user.telegramChatId != str(chatId):
                logging.info(f'Updating Telegram chat ID for user {user.userId} from {user.telegramChatId} to {chatId}')
                await self.databaseStore.update_user_telegram(
                    userId=user.userId,
                    telegramId=senderUsername,
                    telegramChatId=str(chatId),
                    telegramUsername=senderUsername,
                )
            if messageText.startswith('/start'):
                await self.telegramClient.send_message(
                    chatId=str(chatId),
                    text='Welcome back! Your Telegram is already linked. You will receive notifications about your BorrowBot positions here.',
                )
            else:
                await self.telegramClient.send_message(
                    chatId=str(chatId),
                    text='BorrowBot is currently in notification-only mode. Check your positions at the web app.',
                )
        except NotFoundException:
            await self.telegramClient.send_login_message(chatId=str(chatId), senderUsername=senderUsername)

    async def disconnect_telegram(self, user_address: str) -> UserConfig:
        normalizedAddress = chain_util.normalize_address(user_address)
        user = await self.databaseStore.get_or_create_user_by_wallet(walletAddress=normalizedAddress)
        await self.databaseStore.update_user_telegram(
            userId=user.userId,
            telegramId=None,
            telegramChatId=None,
            telegramUsername=None,
        )
        updatedConfig = UserConfig(telegram_handle=None, telegram_chat_id=None, preferred_ltv=0.75)
        self._userConfigsCache[normalizedAddress] = updatedConfig
        return updatedConfig

    def check_ens_name_available(self, label: str) -> tuple[bool, str, str | None]:
        """Check if an ENS subdomain label is available."""
        isValid, errorMsg = self.ensClient.validate_label(label)
        if not isValid:
            return False, self.ensClient.get_full_ens_name(label), errorMsg
        isAvailable = self.ensClient.check_name_available(label)
        fullName = self.ensClient.get_full_ens_name(label)
        return isAvailable, fullName, None if isAvailable else 'Name is already taken'

    def reserve_ens_name(self, label: str) -> str:
        """Reserve an ENS name and return the full ENS name."""
        return self.ensClient.reserve_name(label)

    async def get_ens_config_transactions(self, userAddress: str, collateral: str | None, targetLtv: int | None, maxLtv: int | None, minLtv: int | None, autoRebalance: bool, riskTolerance: str, description: str | None) -> tuple[list[TransactionCall], str]:
        """Get transactions to set ENS text records for agent configuration."""
        normalizedAddress = chain_util.normalize_address(userAddress)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise NotFoundException(message='User not found')
        agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
        if not agents:
            raise NotFoundException(message='No agents found for user')
        agent = agents[0]
        if not agent.ensName:
            raise ValueError('Agent does not have an ENS name')
        config = EnsAgentConfig(
            collateral=collateral,
            target_ltv=targetLtv,
            max_ltv=maxLtv,
            min_ltv=minLtv,
            auto_rebalance=autoRebalance,
            risk_tolerance=riskTolerance,
            emoji=agent.emoji,
            description=description,
        )
        transactions = self.ensClient.build_set_agent_config_transactions(agent.ensName, config)
        return transactions, agent.ensName
