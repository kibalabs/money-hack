import os
from typing import Any
from urllib.parse import quote_plus

from core.caching.file_cache import FileCache
from core.requester import Requester
from core.store.database import Database
from core.web3.eth_client import RestEthClient

from money_hack import constants
from money_hack.agent.chat_bot import ChatBot
from money_hack.agent.chat_history_store import ChatHistoryStore
from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.gemini_llm import GeminiLLM
from money_hack.agent.tools import GetActionHistoryTool
from money_hack.agent.tools import GetMarketDataTool
from money_hack.agent.tools import GetPositionTool
from money_hack.agent.tools import GetPriceAnalysisTool
from money_hack.agent.tools import SetTargetLtvTool
from money_hack.blockchain_data.price_intelligence_service import PriceIntelligenceService
from money_hack.agent_manager import AgentManager
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.blockchain_data.findblock_client import FindBlockClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.external.coinbase_cdp_client import CoinbaseCdpClient
from money_hack.external.ens_client import EnsClient
from money_hack.external.telegram_client import TelegramClient
from money_hack.forty_acres.forty_acres_client import FortyAcresClient
from money_hack.morpho.ltv_manager import LtvManager
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.notification_service import NotificationService
from money_hack.smart_wallets.coinbase_bundler import CoinbaseBundler
from money_hack.smart_wallets.coinbase_smart_wallet import CoinbaseSmartWallet
from money_hack.store.database_store import DatabaseStore

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ['BASE_RPC_URL']
BASE_PAYMASTER_RPC_URL = os.environ['BASE_PAYMASTER_RPC_URL']
CDP_WALLET_SECRET = os.environ['CDP_WALLET_SECRET']
CDP_API_KEY_NAME = os.environ['CDP_API_KEY_NAME']
CDP_API_KEY_PRIVATE_KEY = os.environ['CDP_API_KEY_PRIVATE_KEY']
DEPLOYER_PRIVATE_KEY = os.environ['DEPLOYER_PRIVATE_KEY']
MORALIS_API_KEY = os.environ['MORALIS_API_KEY']
ALCHEMY_API_KEY = os.environ['ALCHEMY_API_KEY']
BLOCKSCOUT_API_KEY = os.environ['BLOCKSCOUT_API_KEY']
TELEGRAM_API_TOKEN = os.environ['TELEGRAM_API_TOKEN']
GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
API_URL = os.environ['KRT_API_URL']
APP_URL = os.environ['KRT_APP_URL']
DB_HOST = os.environ['DB_HOST']
DB_PORT = os.environ['DB_PORT']
DB_NAME = os.environ['DB_NAME']
DB_USERNAME = os.environ['DB_USERNAME']
DB_PASSWORD = os.environ['DB_PASSWORD']


def create_agent_manager() -> AgentManager:
    requester = Requester()
    cache = FileCache(cacheDirectory='./data/cache')
    ethClient = RestEthClient(url=BASE_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester)
    paymasterEthClient = RestEthClient(url=BASE_PAYMASTER_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester) if BASE_PAYMASTER_RPC_URL else None
    moralisClient = MoralisClient(requester=requester, apiKey=MORALIS_API_KEY, cache=cache)
    findBlockClient = FindBlockClient(requester=requester, cache=cache)
    alchemyClient = AlchemyClient(requester=requester, apiKey=ALCHEMY_API_KEY, cache=cache, findBlockClient=findBlockClient)
    morphoClient = MorphoClient(requester=requester)
    blockscoutClient = BlockscoutClient(requester=requester, cache=cache, apiKey=BLOCKSCOUT_API_KEY)
    fortyAcresClient = FortyAcresClient(requester=requester, ethClient=ethClient, blockscoutClient=blockscoutClient)
    telegramClient = TelegramClient(
        requester=requester,
        botToken=TELEGRAM_API_TOKEN,
        appUrl=APP_URL,
        redirectUri=f'{API_URL}/v1/telegram-oauth-callback',
        origin=APP_URL,
    )
    ensClient = EnsClient(requester=requester, chainId=BASE_CHAIN_ID)
    coinbaseCdpClient = (
        CoinbaseCdpClient(
            requester=requester,
            walletSecret=CDP_WALLET_SECRET,
            apiKeyName=CDP_API_KEY_NAME,
            apiKeyPrivateKey=CDP_API_KEY_PRIVATE_KEY,
        )
        if CDP_WALLET_SECRET and CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY
        else None
    )
    coinbaseSmartWallet = CoinbaseSmartWallet(ethClient=ethClient) if paymasterEthClient else None
    coinbaseBundler = CoinbaseBundler(paymasterEthClient=paymasterEthClient) if paymasterEthClient else None
    encodedPassword = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    databaseConnectionString = f'postgresql+asyncpg://{DB_USERNAME}:{encodedPassword}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    database = Database(connectionString=databaseConnectionString)
    databaseStore = DatabaseStore(database=database)
    geminiLlm = GeminiLLM(apiKey=GEMINI_API_KEY, requester=requester) if GEMINI_API_KEY else None
    chatHistoryStore = ChatHistoryStore(database=database)
    priceIntelligenceService = PriceIntelligenceService(alchemyClient=alchemyClient, requester=requester)
    chatTools: list[ChatTool[Any, Any]] = [  # type: ignore[explicit-any]
        GetPositionTool(),
        GetMarketDataTool(),
        GetActionHistoryTool(),
        SetTargetLtvTool(),
        GetPriceAnalysisTool(),
    ]
    chatBot = ChatBot(llm=geminiLlm, historyStore=chatHistoryStore, tools=chatTools) if geminiLlm else None

    # LTV Monitoring Setup
    usdcAddress = constants.CHAIN_USDC_MAP.get(BASE_CHAIN_ID)
    yoVaultAddress = '0x0000000f2eB9f69274678c76222B35eEc7588a65'
    ltvManager = None
    notificationService = None
    if usdcAddress:
        ltvManager = LtvManager(
            chainId=BASE_CHAIN_ID,
            usdcAddress=usdcAddress,
            yoVaultAddress=yoVaultAddress,
            morphoClient=morphoClient,
            alchemyClient=alchemyClient,
            databaseStore=databaseStore,
            priceIntelligenceService=priceIntelligenceService,
            fortyAcresClient=fortyAcresClient,
        )
        notificationService = NotificationService(
            telegramClient=telegramClient,
            databaseStore=databaseStore,
        )

    agentManager = AgentManager(
        requester=requester,
        chainId=BASE_CHAIN_ID,
        ethClient=ethClient,
        moralisClient=moralisClient,
        alchemyClient=alchemyClient,
        morphoClient=morphoClient,
        fortyAcresClient=fortyAcresClient,
        telegramClient=telegramClient,
        ensClient=ensClient,
        databaseStore=databaseStore,
        coinbaseCdpClient=coinbaseCdpClient,
        coinbaseSmartWallet=coinbaseSmartWallet,
        coinbaseBundler=coinbaseBundler,
        deployerPrivateKey=DEPLOYER_PRIVATE_KEY,
        chatBot=chatBot,
        chatHistoryStore=chatHistoryStore,
        ltvManager=ltvManager,
        notificationService=notificationService,
        priceIntelligenceService=priceIntelligenceService,
    )
    return agentManager
