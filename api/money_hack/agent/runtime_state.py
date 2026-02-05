from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from money_hack.agent_manager import AgentManager


class RuntimeState(BaseModel):
    """Runtime state passed to chat tools during execution."""

    class Config:
        arbitrary_types_allowed = True

    userId: str
    agentId: str
    conversationId: str
    walletAddress: str
    chainId: int
    agentManager: AgentManager

    def __init__(
        self,
        userId: str,
        agentId: str,
        conversationId: str,
        walletAddress: str,
        chainId: int,
        agentManager: AgentManager,
    ) -> None:
        super().__init__(
            userId=userId,
            agentId=agentId,
            conversationId=conversationId,
            walletAddress=walletAddress,
            chainId=chainId,
            agentManager=agentManager,
        )
