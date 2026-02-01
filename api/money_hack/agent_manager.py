from core.requester import Requester

from money_hack.api.authorizer import Authorizer


class AgentManager(Authorizer):
    def __init__(
        self,
        requester: Requester,
        chainId: int,
    ) -> None:
        self.chainId = chainId
        self.requester = requester
