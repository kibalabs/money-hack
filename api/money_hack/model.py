from __future__ import annotations

import datetime

from core.util.typing_util import JsonObject
from pydantic import BaseModel


class User(BaseModel):
    userId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    username: str
    telegramId: str | None
    telegramChatId: str | None
    telegramUsername: str | None


class UserWallet(BaseModel):
    userWalletId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    walletAddress: str


class Agent(BaseModel):
    agentId: str
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    name: str
    emoji: str
    agentIndex: int
    walletAddress: str
    ensName: str | None


class AgentPosition(BaseModel):
    agentPositionId: int
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    agentId: str
    collateralAsset: str
    targetLtv: float
    morphoMarketId: str
    status: str


class AgentAction(BaseModel):
    agentActionId: int
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    agentId: str
    actionType: str
    value: str
    valueId: str | None
    details: JsonObject


class ChatEvent(BaseModel):
    chatEventId: int
    createdDate: datetime.datetime
    updatedDate: datetime.datetime
    userId: str
    agentId: str
    conversationId: str
    eventType: str
    content: str | JsonObject
