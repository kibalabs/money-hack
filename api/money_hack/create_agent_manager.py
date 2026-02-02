import os
from pathlib import Path

from core.caching.file_cache import FileCache
from core.requester import Requester
from core.web3.eth_client import RestEthClient

from money_hack.agent_manager import AgentManager
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.blockchain_data.findblock_client import FindBlockClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.external.telegram_client import TelegramClient
from money_hack.forty_acres.forty_acres_client import FortyAcresClient
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.store.file_store import FileStore

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')
MORALIS_API_KEY = os.environ.get('MORALIS_API_KEY', '')
ALCHEMY_API_KEY = os.environ.get('ALCHEMY_API_KEY', '')
BLOCKSCOUT_API_KEY = os.environ.get('BLOCKSCOUT_API_KEY', '')
TELEGRAM_API_TOKEN = os.environ.get('TELEGRAM_API_TOKEN', '')
MONEY_HACK_API_URL = os.environ.get('MONEY_HACK_API_URL', 'http://localhost:8000')
MONEY_HACK_APP_URL = os.environ.get('MONEY_HACK_APP_URL', 'http://localhost:3000')

DATA_DIR = Path(os.environ.get('DATA_DIR', './data'))


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
        appUrl=MONEY_HACK_APP_URL,
        redirectUri=f'{MONEY_HACK_API_URL}/v1/telegram-oauth-callback',
        origin=MONEY_HACK_APP_URL,
    )
    fileStore = FileStore(dataDir=DATA_DIR)
    agentManager = AgentManager(
        requester=requester,
        chainId=BASE_CHAIN_ID,
        ethClient=ethClient,
        moralisClient=moralisClient,
        alchemyClient=alchemyClient,
        morphoClient=morphoClient,
        fortyAcresClient=fortyAcresClient,
        telegramClient=telegramClient,
        fileStore=fileStore,
    )
    return agentManager
