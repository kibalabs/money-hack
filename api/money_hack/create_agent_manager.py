import os

from core.caching.file_cache import FileCache
from core.requester import Requester
from core.web3.eth_client import RestEthClient

from money_hack.agent_manager import AgentManager
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.blockchain_data.findblock_client import FindBlockClient
from money_hack.blockchain_data.moralis_client import MoralisClient
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.yo.yo_client import YoClient

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')
MORALIS_API_KEY = os.environ.get('MORALIS_API_KEY', '')
ALCHEMY_API_KEY = os.environ.get('ALCHEMY_API_KEY', '')
BLOCKSCOUT_API_KEY = os.environ.get('BLOCKSCOUT_API_KEY', '')


def create_agent_manager() -> AgentManager:
    requester = Requester()
    cache = FileCache(cacheDirectory='./data/cache')
    ethClient = RestEthClient(url=BASE_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester)
    moralisClient = MoralisClient(requester=requester, apiKey=MORALIS_API_KEY, cache=cache)
    findBlockClient = FindBlockClient(requester=requester, cache=cache)
    alchemyClient = AlchemyClient(requester=requester, apiKey=ALCHEMY_API_KEY, cache=cache, findBlockClient=findBlockClient)
    morphoClient = MorphoClient(requester=requester)
    blockscoutClient = BlockscoutClient(requester=requester, cache=cache, apiKey=BLOCKSCOUT_API_KEY)
    yoClient = YoClient(requester=requester, ethClient=ethClient, blockscoutClient=blockscoutClient)
    agentManager = AgentManager(
        requester=requester,
        chainId=BASE_CHAIN_ID,
        ethClient=ethClient,
        moralisClient=moralisClient,
        alchemyClient=alchemyClient,
        morphoClient=morphoClient,
        yoClient=yoClient,
    )
    return agentManager
