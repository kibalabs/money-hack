from __future__ import annotations

from typing import TYPE_CHECKING

from core.store.retriever import Direction
from core.store.retriever import FieldFilter
from core.store.retriever import Order
from core.store.retriever import StringFieldFilter
from core.util.typing_util import JsonObject

from money_hack.model import ChatEvent
from money_hack.store.schema import ChatEventsRepository
from money_hack.store.schema import ChatEventsTable

if TYPE_CHECKING:
    from core.store.database import Database


class ChatHistoryStore:
    """Store for chat conversation history."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def add_event(
        self,
        userId: str,
        agentId: str,
        conversationId: str,
        eventType: str,
        content: str | JsonObject,
    ) -> ChatEvent:
        """Add a chat event to the history."""
        contentDict = {'text': content} if isinstance(content, str) else content
        return await ChatEventsRepository.create(
            database=self.database,
            userId=userId,
            agentId=agentId,
            conversationId=conversationId,
            eventType=eventType,
            content=contentDict,
        )

    async def list_events(
        self,
        userId: str,
        agentId: str,
        conversationId: str,
        maxEvents: int = 20,
        shouldIncludeSteps: bool = True,
        shouldIncludePrompts: bool = True,
        shouldIncludeTools: bool = True,
    ) -> list[ChatEvent]:
        """List chat events for a conversation, most recent first then reversed."""
        fieldFilters: list[FieldFilter] = [
            StringFieldFilter(fieldName=ChatEventsTable.c.userId.key, eq=userId),
            StringFieldFilter(fieldName=ChatEventsTable.c.agentId.key, eq=agentId),
            StringFieldFilter(fieldName=ChatEventsTable.c.conversationId.key, eq=conversationId),
        ]
        if not shouldIncludeSteps:
            fieldFilters.append(StringFieldFilter(fieldName=ChatEventsTable.c.eventType.key, ne='step'))
        if not shouldIncludePrompts:
            fieldFilters.append(StringFieldFilter(fieldName=ChatEventsTable.c.eventType.key, ne='prompt'))
        if not shouldIncludeTools:
            fieldFilters.append(StringFieldFilter(fieldName=ChatEventsTable.c.eventType.key, ne='tool'))
        events = await ChatEventsRepository.list_many(
            database=self.database,
            fieldFilters=fieldFilters,
            orders=[
                Order(fieldName=ChatEventsTable.c.createdDate.key, direction=Direction.DESCENDING),
            ],
            limit=maxEvents,
        )
        return list(reversed(events))

    async def get_user_agent_events(
        self,
        userId: str,
        agentId: str,
        conversationId: str,
        maxEvents: int = 50,
    ) -> list[ChatEvent]:
        """Get only user and agent message events (for display)."""
        fieldFilters: list[FieldFilter] = [
            StringFieldFilter(fieldName=ChatEventsTable.c.userId.key, eq=userId),
            StringFieldFilter(fieldName=ChatEventsTable.c.agentId.key, eq=agentId),
            StringFieldFilter(fieldName=ChatEventsTable.c.conversationId.key, eq=conversationId),
        ]
        events = await ChatEventsRepository.list_many(
            database=self.database,
            fieldFilters=fieldFilters,
            orders=[
                Order(fieldName=ChatEventsTable.c.createdDate.key, direction=Direction.DESCENDING),
            ],
            limit=maxEvents * 2,
        )
        filtered = [e for e in events if e.eventType in ('user', 'agent')][:maxEvents]
        return list(reversed(filtered))
