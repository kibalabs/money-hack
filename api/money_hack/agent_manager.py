import asyncio
import base64
import typing
import uuid
from datetime import UTC
from datetime import datetime

from core import logging
from core.exceptions import BadRequestException
from core.exceptions import KibaException
from core.exceptions import NotFoundException
from core.exceptions import UnauthorizedException
from core.requester import Requester
from core.util import chain_util
from core.web3.eth_client import ABI
from core.web3.eth_client import EncodedCall
from core.web3.eth_client import RestEthClient
from eth_account import Account
from eth_account.messages import _hash_eip191_message
from eth_account.messages import encode_defunct
from hexbytes import HexBytes
from siwe import SiweMessage  # type: ignore[import-untyped]
from web3 import Web3
from web3.types import TxParams

from money_hack import constants
from money_hack.agent.chat_bot import ChatBot
from money_hack.agent.chat_history_store import ChatHistoryStore
from money_hack.agent.constants import BORROWBOT_SYSTEM_PROMPT
from money_hack.agent.constants import BORROWBOT_USER_PROMPT
from money_hack.agent.constants import TELEGRAM_FORMATTING_NOTE
from money_hack.agent.runtime_state import RuntimeState
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
from money_hack.morpho.ltv_manager import LtvManager
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.morpho.transaction_builder import TransactionBuilder
from money_hack.notification_service import NotificationService
from money_hack.smart_wallets.coinbase_bundler import CoinbaseBundler
from money_hack.smart_wallets.coinbase_constants import COINBASE_EIP7702PROXY_ADDRESS
from money_hack.smart_wallets.coinbase_constants import COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS
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
        coinbaseCdpClient: CoinbaseCdpClient | None,
        coinbaseSmartWallet: CoinbaseSmartWallet | None,
        coinbaseBundler: CoinbaseBundler | None,
        deployerPrivateKey: str,
        chatBot: ChatBot | None = None,
        chatHistoryStore: ChatHistoryStore | None = None,
        ltvManager: LtvManager | None = None,
        notificationService: NotificationService | None = None,
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
        self.deployerPrivateKey = deployerPrivateKey
        self.ltvManager = ltvManager
        self.notificationService = notificationService
        self.deployerAddress = Account.from_key(deployerPrivateKey).address if deployerPrivateKey else None
        self.deployerTransactionLock = asyncio.Lock()
        self.chatBot = chatBot
        self.chatHistoryStore = chatHistoryStore
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
            userAddress=normalizedAddress,
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

    async def _make_deployer_transaction(self, params: TxParams, maxRetryCount: int = 3) -> str:
        if self.deployerPrivateKey is None or self.deployerAddress is None:
            raise BadRequestException('Deployer private key is not configured')
        async with self.deployerTransactionLock:
            baseParams = await self.ethClient.fill_transaction_params(params=params, fromAddress=self.deployerAddress)
            retryCount = 0
            while True:
                paramsToSend = dict(baseParams)
                if retryCount > 0:
                    multiplier = 1 + (retryCount * 0.15)
                    paramsToSend['gas'] = int(baseParams['gas'] * multiplier)
                    paramsToSend['maxFeePerGas'] = hex(int(int(baseParams['maxFeePerGas'], 16) * multiplier))  # type: ignore[arg-type]
                    paramsToSend['maxPriorityFeePerGas'] = hex(int(int(baseParams['maxPriorityFeePerGas'], 16) * multiplier))  # type: ignore[arg-type]
                signedParams = self.ethClient.w3.eth.account.sign_transaction(transaction_dict=paramsToSend, private_key=self.deployerPrivateKey)
                transactionHash = await self.ethClient.send_raw_transaction(transactionData=signedParams.raw_transaction.hex())
                logging.info(f'Sending deployer transaction (retry={retryCount}): {transactionHash}')
                try:
                    await self.ethClient.wait_for_transaction_receipt(transactionHash=transactionHash)
                    logging.info(f'Deployer transaction confirmed: {transactionHash}')
                    return transactionHash  # noqa: TRY300
                except BadRequestException as exception:
                    if not exception.message or 'replacement transaction underpriced' not in exception.message:
                        raise
                    if retryCount >= (maxRetryCount - 1):
                        raise
                    retryCount += 1

    async def _sign_hash_with_cdp(self, messageHash: str, walletAddress: str) -> str:
        if self.coinbaseCdpClient is None:
            raise BadRequestException('Coinbase CDP client is not configured')
        return await self.coinbaseCdpClient.sign_hash(walletAddress=walletAddress, messageHash=messageHash)

    async def _set_delegation(self, agentWalletAddress: str, userAddress: str) -> None:
        if self.coinbaseSmartWallet is None or self.deployerPrivateKey is None:
            raise BadRequestException('Smart wallet or deployer is not configured')
        currentDelegationStatus = await self.coinbaseSmartWallet.get_eoa_delegation_status(address=agentWalletAddress)
        if currentDelegationStatus.isDelegatedToCoinbaseSmartWallet:
            return
        upgradeData = hex(0)
        if currentDelegationStatus.implementationAddress != COINBASE_SMART_WALLET_IMPLEMENTATION_ADDRESS:
            initArgs = self.coinbaseSmartWallet.encode_initialize_call(owners=[agentWalletAddress, userAddress])
            setImplementationHash = await self.coinbaseSmartWallet.create_set_implementation_hash(
                address=agentWalletAddress,
                callData=initArgs,
                currentImplementationAddress=currentDelegationStatus.implementationAddress or chain_util.BURN_ADDRESS,
            )
            signedSetImplementationHash = await self._sign_hash_with_cdp(messageHash=setImplementationHash, walletAddress=agentWalletAddress)
            upgradeData = self.coinbaseSmartWallet.encode_set_implementation_call(
                initArgs=initArgs,
                signedSetImplementationHash=signedSetImplementationHash,
            )
        unsignedAuthorization = await self.coinbaseSmartWallet.build_unsigned_authorization(
            walletAddress=agentWalletAddress,
            targetAddress=COINBASE_EIP7702PROXY_ADDRESS,
            isUserMakingTransaction=False,
        )
        authHash = unsignedAuthorization.hash().hex()
        authSignatureHex = await self._sign_hash_with_cdp(messageHash=authHash, walletAddress=agentWalletAddress)
        signedAuth = self.coinbaseSmartWallet.build_signed_authorization(
            unsignedAuthorization=unsignedAuthorization,
            authSignatureHex=authSignatureHex,
        )
        params = await self.coinbaseSmartWallet.build_delegation_transaction_params(
            walletAddress=agentWalletAddress,
            signedAuthorization=signedAuth,
            data=upgradeData,
        )
        await self._make_deployer_transaction(params=params)
        logging.info(f'Delegation set for {agentWalletAddress}')

    async def _send_user_operation(self, agentWalletAddress: str, calls: list[EncodedCall]) -> str:
        if self.coinbaseSmartWallet is None or self.coinbaseBundler is None or self.coinbaseCdpClient is None:
            raise BadRequestException('Smart wallet infrastructure is not configured')
        self.coinbaseBundler.validate_calls(calls=calls, chainId=self.chainId)
        await self.coinbaseSmartWallet.validate_calls(calls=calls, chainId=self.chainId)
        callData = await self.coinbaseSmartWallet.build_execute_call_data(chainId=self.chainId, calls=calls)
        userOperation = await self.coinbaseBundler.build_user_operation(
            chainId=self.chainId,
            sender=agentWalletAddress,
            callData=callData,
            shouldSponsorGas=True,
        )
        userOpHashToSign = await self.coinbaseBundler.generate_user_operation_hash(userOperation=userOperation)
        signature = await self._sign_hash_with_cdp(messageHash=userOpHashToSign, walletAddress=agentWalletAddress)
        userOperationSignature = self.coinbaseSmartWallet.encode_user_operation_signature(signature=signature)
        userOperationHash = await self.coinbaseBundler.send_user_operation(userOperation=userOperation, signature=userOperationSignature)
        logging.info(f'Sent user operation: {userOperationHash}')
        receipt = await self.coinbaseBundler.wait_for_user_operation_receipt(userOperationHash=userOperationHash, raiseOnFailure=True)
        transactionHash = typing.cast(str, receipt['receipt']['transactionHash'])
        logging.info(f'User operation confirmed: {transactionHash}')
        return transactionHash

    async def monitor_positions_loop(self) -> None:
        if not self.ltvManager or not self.notificationService:
            logging.error('LTV Manager or Notification Service not configured. Monitor loop aborted.')
            return

        LTV_CHECK_INTERVAL_SECONDS = 300
        CRITICAL_LTV_THRESHOLD = 0.80
        WARN_INTERVAL_HOURS = 4
        URGENT_INTERVAL_HOURS = 1

        while True:
            try:
                positions = await self.databaseStore.get_all_active_positions()
                logging.info(f'Checking LTV for {len(positions)} active positions')
                for position in positions:
                    try:
                        result = await self.ltvManager.check_position_ltv(position)
                        await self.ltvManager.log_ltv_check(result)

                        agent = await self.databaseStore.get_agent(agentId=position.agentId)
                        if not agent:
                            continue
                        user = await self.databaseStore.get_user(userId=agent.userId)
                        if not user:
                            continue

                        # Handle Action
                        if result.needs_action and result.action_type == 'auto_repay':
                            logging.info(f'Position {position.agentPositionId}: Auto-repaying {result.action_amount} USDC')
                            try:
                                actionTx = await self.ltvManager.build_auto_repay_transactions(
                                    position=position,
                                    repayAmount=result.action_amount or 0,
                                    userAddress=agent.walletAddress,
                                )
                                calls = [EncodedCall(toAddress=tx.to, data=HexBytes(tx.data).hex(), value=int(tx.value)) for tx in actionTx.transactions]
                                await self._send_user_operation(
                                    agentWalletAddress=agent.walletAddress,
                                    calls=calls,
                                )
                                await self.notificationService.send_auto_repay_success(
                                    agent=agent,
                                    user=user,
                                    repayAmount=float(result.action_amount or 0) / 1e6,  # Assuming 6 decimals for USDC
                                    oldLtv=result.current_ltv,
                                    newLtv=result.target_ltv,  # Approximate new LTV
                                )
                            except Exception:  # noqa: BLE001
                                logging.exception(f'Failed to auto-repay for position {position.agentPositionId}')
                                # Fallback to warning handled below if condition persists next check

                        # Handle Warnings (Manual Repay or Critical Threshold)
                        currentLtv = result.current_ltv
                        maxLtv = result.max_ltv
                        isCritical = currentLtv >= CRITICAL_LTV_THRESHOLD * maxLtv and maxLtv > 0
                        if (result.needs_action and result.action_type == 'manual_repay') or isCritical:
                            lastWarning = await self.databaseStore.get_latest_action_by_type(agent.agentId, 'critical_ltv_warning')
                            shouldWarn = True
                            if lastWarning:
                                timeSince = datetime.now(tz=UTC) - lastWarning.createdDate.replace(tzinfo=UTC)
                                interval = URGENT_INTERVAL_HOURS if isCritical else WARN_INTERVAL_HOURS
                                if timeSince.total_seconds() < interval * 3600:
                                    shouldWarn = False

                            if shouldWarn:
                                await self.notificationService.send_critical_ltv_warning(
                                    agent=agent,
                                    user=user,
                                    currentLtv=currentLtv,
                                    maxLtv=maxLtv,
                                )
                        elif result.needs_action:
                            logging.warning(f'Position {position.agentPositionId} needs action: {result.action_type} - {result.reason}')

                        # Daily Digest
                        lastDigest = await self.databaseStore.get_latest_action_by_type(agent.agentId, 'daily_digest')
                        shouldSendDigest = True
                        if lastDigest:
                            # Use aware datetime for comparison
                            lastCreated = lastDigest.createdDate.replace(tzinfo=UTC) if lastDigest.createdDate.tzinfo is None else lastDigest.createdDate
                            timeSince = datetime.now(tz=UTC) - lastCreated
                            if timeSince.total_seconds() < 24 * 3600:
                                shouldSendDigest = False

                        if shouldSendDigest and not result.needs_action and not isCritical:
                            priceData = await self.alchemyClient.get_asset_current_price(chainId=self.chainId, assetAddress=position.collateralAsset)
                            collateralValue = (position.collateralAmount / 1e18) * priceData.priceUsd
                            debtValue = position.borrowAmount / 1e6
                            await self.notificationService.send_daily_digest(
                                agent=agent,
                                user=user,
                                currentLtv=currentLtv,
                                collateralValue=collateralValue,
                                debtValue=debtValue,
                            )

                    except Exception:  # noqa: BLE001
                        logging.exception(f'Error checking position {position.agentPositionId}')
            except Exception:  # noqa: BLE001
                logging.exception('Error in position monitoring loop')
            await asyncio.sleep(LTV_CHECK_INTERVAL_SECONDS)

    async def _execute_agent_deploy_transactions(self, agentWalletAddress: str, userAddress: str, collateralAssetAddress: str, collateralAmount: str, targetLtv: float) -> str | None:
        if self.coinbaseCdpClient is None or self.coinbaseSmartWallet is None or self.coinbaseBundler is None or self.deployerPrivateKey is None:
            return None
        await self._set_delegation(agentWalletAddress=agentWalletAddress, userAddress=userAddress)
        transactionsData = await self._build_position_transactions(
            userAddress=agentWalletAddress,
            collateralAssetAddress=collateralAssetAddress,
            collateralAmount=collateralAmount,
            targetLtv=targetLtv,
        )
        calls = [
            EncodedCall(
                toAddress=tx.to,
                data=tx.data if tx.data.startswith('0x') else f'0x{tx.data}',
                value=int(tx.value or '0'),
            )
            for tx in transactionsData.transactions
        ]
        if not calls:
            return None
        transactionHash = await self._send_user_operation(agentWalletAddress=agentWalletAddress, calls=calls)
        return transactionHash

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
                    text='Welcome back! Your Telegram is already linked. You can now chat with your BorrowBot agent here. Try asking "What\'s my position?" or "What are the current rates?"',
                )
            else:
                agents = await self.databaseStore.get_agents_by_user(userId=user.userId)
                if not agents:
                    await self.telegramClient.send_message(
                        chatId=str(chatId),
                        text="You don't have an agent yet. Please set up a position in the web app first.",
                    )
                    return
                agent = agents[0]
                userWallets = await self.databaseStore.get_user_wallets(userId=user.userId)
                if not userWallets:
                    await self.telegramClient.send_message(
                        chatId=str(chatId),
                        text='No wallet found for your account.',
                    )
                    return
                walletAddress = userWallets[0].walletAddress
                await self.telegramClient.send_message(chatId=str(chatId), text='Thinking...')
                try:
                    messages, _ = await self.send_chat_message(
                        userAddress=walletAddress,
                        agentId=agent.agentId,
                        message=messageText,
                        conversationId=f'telegram_{chatId}',
                        channel='telegram',
                    )
                    agentMessages = [m for m in messages if not m.get('is_user', True)]
                    if agentMessages:
                        for msg in agentMessages:
                            await self.telegramClient.send_message(
                                chatId=str(chatId),
                                text=str(msg.get('content', '')),
                            )
                    else:
                        await self.telegramClient.send_message(
                            chatId=str(chatId),
                            text="I couldn't generate a response. Please try again.",
                        )
                except Exception as e:  # noqa: BLE001
                    logging.error(f'Error processing Telegram chat message: {e}')
                    await self.telegramClient.send_message(
                        chatId=str(chatId),
                        text='Sorry, I encountered an error processing your message. Please try again.',
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

    async def send_chat_message(
        self,
        userAddress: str,
        agentId: str,
        message: str,
        conversationId: str | None = None,
        channel: str = 'web',
    ) -> tuple[list[dict[str, object]], str]:
        """Send a message to the chat and get the agent's response."""
        if self.chatBot is None:
            raise BadRequestException(message='Chat functionality not configured')
        normalizedAddress = chain_util.normalize_address(userAddress)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise NotFoundException(message='User not found')
        agent = await self.databaseStore.get_agent_by_id(agentId=agentId)
        if agent is None or agent.userId != user.userId:
            raise NotFoundException(message='Agent not found')
        if conversationId is None:
            conversationId = f'{channel}_{agentId}'
        runtimeState = RuntimeState(
            userId=user.userId,
            agentId=agentId,
            conversationId=conversationId,
            walletAddress=normalizedAddress,
            chainId=self.chainId,
            databaseStore=self.databaseStore,
            getMarketData=self.get_market_data,
            getPosition=self.get_position,
        )
        systemPrompt = BORROWBOT_SYSTEM_PROMPT.format(agent_name=f'{agent.emoji} {agent.name}')
        userPrompt = BORROWBOT_USER_PROMPT
        if channel == 'telegram':
            systemPrompt += TELEGRAM_FORMATTING_NOTE
        messages: list[dict[str, object]] = []
        async for event in self.chatBot.execute(
            systemPrompt=systemPrompt,
            userPromptTemplate=userPrompt,
            runtimeState=runtimeState,
            userMessage=message,
        ):
            if event.eventType in ('user', 'agent'):
                content = event.content
                text = content.get('text', '') if isinstance(content, dict) else str(content)
                messages.append(
                    {
                        'message_id': event.chatEventId,
                        'created_date': event.createdDate.isoformat(),
                        'is_user': event.eventType == 'user',
                        'content': text,
                    }
                )
        return messages, conversationId

    async def get_chat_history(
        self,
        userAddress: str,
        agentId: str,
        conversationId: str | None = None,
        limit: int = 50,
        channel: str = 'web',
    ) -> tuple[list[dict[str, object]], str]:
        """Get the chat history for an agent."""
        if self.chatHistoryStore is None:
            raise BadRequestException(message='Chat functionality not configured')
        normalizedAddress = chain_util.normalize_address(userAddress)
        user = await self.databaseStore.get_user_by_wallet(walletAddress=normalizedAddress)
        if user is None:
            raise NotFoundException(message='User not found')
        agent = await self.databaseStore.get_agent_by_id(agentId=agentId)
        if agent is None or agent.userId != user.userId:
            raise NotFoundException(message='Agent not found')
        if conversationId is None:
            conversationId = f'{channel}_{agentId}'
        events = await self.chatHistoryStore.get_user_agent_events(
            userId=user.userId,
            agentId=agentId,
            conversationId=conversationId,
            maxEvents=limit,
        )
        messages: list[dict[str, object]] = []
        for event in events:
            content = event.content
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            messages.append(
                {
                    'message_id': event.chatEventId,
                    'created_date': event.createdDate.isoformat(),
                    'is_user': event.eventType == 'user',
                    'content': text,
                }
            )
        return messages, conversationId
