import os

from core.requester import Requester
from core.web3.eth_client import RestEthClient

from money_hack.agent_manager import AgentManager

BASE_CHAIN_ID = 8453
BASE_RPC_URL = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')


def create_agent_manager() -> AgentManager:
    requester = Requester()
    ethClient = RestEthClient(url=BASE_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester)
    agentManager = AgentManager(
        requester=requester,
        chainId=BASE_CHAIN_ID,
        ethClient=ethClient,
    )
    return agentManager
