from core.requester import Requester

from money_hack.agent_manager import AgentManager

# DB_HOST = os.environ['DB_HOST']
# DB_PORT = os.environ['DB_PORT']
# DB_NAME = os.environ['DB_NAME']
# DB_USERNAME = os.environ['DB_USERNAME']
# DB_PASSWORD = os.environ['DB_PASSWORD']


def create_agent_manager() -> AgentManager:
    # database = Database(
    #     connectionString=Database.create_psql_connection_string(
    #         host=DB_HOST,
    #         port=DB_PORT,
    #         name=DB_NAME,
    #         username=DB_USERNAME,
    #         password=DB_PASSWORD,
    #     )
    # )
    requester = Requester()
    agentManager = AgentManager(
        requester=requester,
        chainId=8453,
    )
    return agentManager
