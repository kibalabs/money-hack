from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

from pydantic import BaseModel

from money_hack.store.database_store import DatabaseStore


class RuntimeState(BaseModel):  # type: ignore[explicit-any]
    class Config:
        arbitrary_types_allowed = True

    userId: str
    agentId: str
    conversationId: str
    walletAddress: str
    chainId: int
    databaseStore: DatabaseStore
    getMarketData: Callable[[], Coroutine[Any, Any, Any]]  # type: ignore[explicit-any]
    getPosition: Callable[[str], Coroutine[Any, Any, Any]]  # type: ignore[explicit-any]
    getPriceAnalysis: Callable[[str], Coroutine[Any, Any, Any]] | None = None  # type: ignore[explicit-any]
