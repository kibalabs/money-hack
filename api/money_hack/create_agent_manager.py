import os

from core.caching.file_cache import FileCache
from core.requester import Requester
from core.web3.eth_client import RestEthClient

from money_hack.agent_manager import AgentManager
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.findblock_client import FindBlockClient
from money_hack.blockchain_data.moralis_client import MoralisClient

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')
MORALIS_API_KEY = os.environ.get('MORALIS_API_KEY', '')
ALCHEMY_API_KEY = os.environ.get('ALCHEMY_API_KEY', '')


def create_agent_manager() -> AgentManager:
    requester = Requester()
    cache = FileCache(cacheDirectory='./data/cache')
    ethClient = RestEthClient(url=BASE_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester)

    # Initialize price feed clients
    moralisClient = MoralisClient(requester=requester, apiKey=MORALIS_API_KEY, cache=cache)
    findBlockClient = FindBlockClient(requester=requester, cache=cache)
    alchemyClient = AlchemyClient(requester=requester, apiKey=ALCHEMY_API_KEY, cache=cache, findBlockClient=findBlockClient)

    agentManager = AgentManager(
        requester=requester,
        chainId=BASE_CHAIN_ID,
        ethClient=ethClient,
        moralisClient=moralisClient,
        alchemyClient=alchemyClient,
    )
    return agentManager
