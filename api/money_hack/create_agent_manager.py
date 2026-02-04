import os
from urllib.parse import quote_plus

from core.caching.file_cache import FileCache
from core.requester import Requester
from core.store.database import Database
from core.web3.eth_client import RestEthClient

from money_hack.agent_manager import AgentManager
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.blockchain_data.findblock_client import FindBlockClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.external.ens_client import EnsClient
from money_hack.external.telegram_client import TelegramClient
from money_hack.forty_acres.forty_acres_client import FortyAcresClient
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.store.database_store import DatabaseStore

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ['BASE_RPC_URL']
MORALIS_API_KEY = os.environ['MORALIS_API_KEY']
ALCHEMY_API_KEY = os.environ['ALCHEMY_API_KEY']
BLOCKSCOUT_API_KEY = os.environ['BLOCKSCOUT_API_KEY']
TELEGRAM_API_TOKEN = os.environ['TELEGRAM_API_TOKEN']
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
    encodedPassword = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    databaseConnectionString = f'postgresql+asyncpg://{DB_USERNAME}:{encodedPassword}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    database = Database(connectionString=databaseConnectionString)
    databaseStore = DatabaseStore(database=database)
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
    )
    return agentManager
