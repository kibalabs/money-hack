from core.exceptions import NotFoundException
from core.store.database import Database
from core.store.retriever import Direction
from core.store.retriever import FieldFilter
from core.store.retriever import Order
from core.store.retriever import StringFieldFilter
from core.util import chain_util

from money_hack.model import Agent
from money_hack.model import AgentAction
from money_hack.model import AgentPosition
from money_hack.model import ChatEvent
from money_hack.model import CrossChainAction
from money_hack.model import User
from money_hack.model import UserWallet
from money_hack.store.entity_repository import UUIDFieldFilter
from money_hack.store.schema import AgentActionsRepository
from money_hack.store.schema import AgentPositionsRepository
from money_hack.store.schema import AgentsRepository
from money_hack.store.schema import ChatEventsRepository
from money_hack.store.schema import CrossChainActionsRepository
from money_hack.store.schema import UsersRepository
from money_hack.store.schema import UserWalletsRepository


class DatabaseStore:
    """Database-backed storage for users, agents, positions, and chat events."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_user(self, userId: str) -> User | None:
        return await UsersRepository.get_one_or_none(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='userId', eq=userId)],
        )

    async def get_user_by_wallet(self, walletAddress: str) -> User | None:
        normalizedAddress = chain_util.normalize_address(walletAddress)
        userWallet = await UserWalletsRepository.get_one_or_none(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName='walletAddress', eq=normalizedAddress)],
        )
        if userWallet is None:
            return None
        return await UsersRepository.get(database=self.database, idValue=userWallet.userId)

    async def get_user_by_telegram_id(self, telegramId: str) -> User:
        user = await UsersRepository.get_one_or_none(
            database=self.database,
            fieldFilters=[StringFieldFilter(fieldName='telegramId', eq=telegramId)],
        )
        if user is None:
            raise NotFoundException(message=f'User with telegram_id {telegramId} not found')
        return user

    async def get_or_create_user_by_wallet(self, walletAddress: str) -> User:
        normalizedAddress = chain_util.normalize_address(walletAddress)
        existingUser = await self.get_user_by_wallet(walletAddress=normalizedAddress)
        if existingUser is not None:
            return existingUser
        shortAddress = normalizedAddress[:10].lower()
        user = await UsersRepository.create(
            database=self.database,
            username=shortAddress,
            telegramId=None,
            telegramChatId=None,
            telegramUsername=None,
        )
        await UserWalletsRepository.create(
            database=self.database,
            userId=user.userId,
            walletAddress=normalizedAddress,
        )
        return user

    async def update_user_telegram(self, userId: str, telegramId: str | None, telegramChatId: str | None, telegramUsername: str | None) -> User:
        return await UsersRepository.update(
            database=self.database,
            userId=userId,
            telegramId=telegramId,
            telegramChatId=telegramChatId,
            telegramUsername=telegramUsername,
        )

    async def get_user_wallets(self, userId: str) -> list[UserWallet]:
        wallets = await UserWalletsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='userId', eq=userId)],
        )
        return wallets

    async def get_agent(self, agentId: str) -> Agent | None:
        return await AgentsRepository.get_one_or_none(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='agentId', eq=agentId)],
        )

    async def get_agent_by_id(self, agentId: str) -> Agent | None:
        return await self.get_agent(agentId=agentId)

    async def get_agents_by_user(self, userId: str) -> list[Agent]:
        return await AgentsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='userId', eq=userId)],
        )

    async def get_agent_by_user_and_index(self, userId: str, agentIndex: int) -> Agent | None:
        agents = await AgentsRepository.list_many(
            database=self.database,
            fieldFilters=[
                UUIDFieldFilter(fieldName='userId', eq=userId),
            ],
        )
        return next((a for a in agents if a.agentIndex == agentIndex), None)

    async def create_agent(self, userId: str, name: str, emoji: str, walletAddress: str, ensName: str | None = None) -> Agent:
        existingAgents = await self.get_agents_by_user(userId=userId)
        agentIndex = len(existingAgents)
        return await AgentsRepository.create(
            database=self.database,
            userId=userId,
            name=name,
            emoji=emoji,
            agentIndex=agentIndex,
            walletAddress=walletAddress,
            ensName=ensName,
        )

    async def update_agent(self, agentId: str, name: str | None = None, emoji: str | None = None, ensName: str | None = None) -> Agent:
        return await AgentsRepository.update(
            database=self.database,
            agentId=agentId,
            name=name,
            emoji=emoji,
            ensName=ensName,
        )

    async def get_position_by_agent(self, agentId: str) -> AgentPosition | None:
        return await AgentPositionsRepository.get_first(
            database=self.database,
            fieldFilters=[
                UUIDFieldFilter(fieldName='agentId', eq=agentId),
                StringFieldFilter(fieldName='status', eq='active'),
            ],
        )

    async def get_all_active_positions(self) -> list[AgentPosition]:
        return await AgentPositionsRepository.list_many(
            database=self.database,
            fieldFilters=[
                StringFieldFilter(fieldName='status', eq='active'),
            ],
        )

    async def create_position(
        self,
        agentId: str,
        collateralAsset: str,
        targetLtv: float,
        morphoMarketId: str,
    ) -> AgentPosition:
        return await AgentPositionsRepository.create(
            database=self.database,
            agentId=agentId,
            collateralAsset=collateralAsset,
            targetLtv=targetLtv,
            morphoMarketId=morphoMarketId,
            status='active',
        )

    async def update_position(
        self,
        agentPositionId: int,
        targetLtv: float | None = None,
        status: str | None = None,
    ) -> AgentPosition:
        kwargs: dict[str, object] = {'agentPositionId': agentPositionId}
        if targetLtv is not None:
            kwargs['targetLtv'] = targetLtv
        if status is not None:
            kwargs['status'] = status
        return await AgentPositionsRepository.update(
            database=self.database,
            connection=None,
            **kwargs,
        )

    async def log_agent_action(
        self,
        agentId: str,
        actionType: str,
        value: str,
        valueId: str | None,
        details: dict[str, object],
    ) -> AgentAction:
        return await AgentActionsRepository.create(
            database=self.database,
            agentId=agentId,
            actionType=actionType,
            value=value,
            valueId=valueId,
            details=details,
        )

    async def get_agent_actions(self, agentId: str, limit: int = 50) -> list[AgentAction]:
        return await AgentActionsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='agentId', eq=agentId)],
            limit=limit,
        )

    async def get_latest_action_by_type(self, agentId: str, actionType: str) -> AgentAction | None:
        actions = await AgentActionsRepository.list_many(
            database=self.database,
            fieldFilters=[
                UUIDFieldFilter(fieldName='agentId', eq=agentId),
                StringFieldFilter(fieldName='actionType', eq=actionType),
            ],
            limit=1,
        )
        return actions[0] if actions else None

    async def create_chat_event(
        self,
        userId: str,
        agentId: str,
        conversationId: str,
        eventType: str,
        content: dict[str, object] | str,
    ) -> ChatEvent:
        contentDict = {'text': content} if isinstance(content, str) else content
        return await ChatEventsRepository.create(
            database=self.database,
            userId=userId,
            agentId=agentId,
            conversationId=conversationId,
            eventType=eventType,
            content=contentDict,
        )

    async def get_chat_events(self, agentId: str, conversationId: str | None = None, limit: int = 100) -> list[ChatEvent]:
        fieldFilters: list[FieldFilter] = [UUIDFieldFilter(fieldName='agentId', eq=agentId)]
        if conversationId is not None:
            fieldFilters.append(StringFieldFilter(fieldName='conversationId', eq=conversationId))
        return await ChatEventsRepository.list_many(
            database=self.database,
            fieldFilters=fieldFilters,
            limit=limit,
        )

    async def set_telegram_secret(self, secretCode: str, walletAddress: str) -> None:
        """Store a temporary telegram secret code mapping to a wallet address.
        We store this as a chat event with a special conversation ID for simplicity.
        In production, you might want a dedicated temp storage table or Redis.
        """
        user = await self.get_or_create_user_by_wallet(walletAddress=walletAddress)
        agents = await self.get_agents_by_user(userId=user.userId)
        agentId = agents[0].agentId if agents else user.userId
        await ChatEventsRepository.create(
            database=self.database,
            userId=user.userId,
            agentId=agentId,
            conversationId=f'telegram_secret:{secretCode}',
            eventType='telegram_auth_pending',
            content={'walletAddress': walletAddress, 'secretCode': secretCode},
        )

    async def get_telegram_secret(self, secretCode: str) -> str | None:
        """Get the wallet address for a telegram secret code."""
        chatEvent = await ChatEventsRepository.get_first(
            database=self.database,
            fieldFilters=[
                StringFieldFilter(fieldName='conversationId', eq=f'telegram_secret:{secretCode}'),
                StringFieldFilter(fieldName='eventType', eq='telegram_auth_pending'),
            ],
        )
        if chatEvent is None:
            return None
        content = chatEvent.content
        if isinstance(content, dict):
            return str(content.get('walletAddress', ''))
        return None

    async def delete_telegram_secret(self, secretCode: str) -> None:
        """Delete a telegram secret code after it's been used."""
        await ChatEventsRepository.delete(
            database=self.database,
            fieldFilters=[
                StringFieldFilter(fieldName='conversationId', eq=f'telegram_secret:{secretCode}'),
                StringFieldFilter(fieldName='eventType', eq='telegram_auth_pending'),
            ],
        )

    async def log_agent_thought(self, agentId: str, thoughtType: str, value: str, details: dict[str, object]) -> AgentAction:
        """Log an agent thought as an action."""
        return await AgentActionsRepository.create(
            database=self.database,
            agentId=agentId,
            actionType=thoughtType,
            value=value,
            valueId=None,
            details=details,
        )

    async def get_agent_thoughts(self, agentId: str, limit: int = 100, hoursBack: int = 24) -> list[AgentAction]:  # noqa: ARG002
        """Get recent agent thoughts (actions with content)."""
        return await AgentActionsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='agentId', eq=agentId)],
            orders=[Order(fieldName='createdDate', direction=Direction.DESCENDING)],
            limit=limit,
        )

    async def create_cross_chain_action(
        self,
        agentId: str,
        actionType: str,
        fromChain: int,
        toChain: int,
        fromToken: str,
        toToken: str,
        amount: str,
        txHash: str | None,
        bridgeName: str | None,
        status: str,
        details: dict[str, object],
    ) -> CrossChainAction:
        return await CrossChainActionsRepository.create(
            database=self.database,
            agentId=agentId,
            actionType=actionType,
            fromChain=fromChain,
            toChain=toChain,
            fromToken=fromToken,
            toToken=toToken,
            amount=amount,
            txHash=txHash,
            bridgeName=bridgeName,
            status=status,
            details=details,
        )

    async def get_pending_cross_chain_actions(self, agentId: str) -> list[CrossChainAction]:
        return await CrossChainActionsRepository.list_many(
            database=self.database,
            fieldFilters=[
                UUIDFieldFilter(fieldName='agentId', eq=agentId),
                StringFieldFilter(fieldName='status', containedIn=['pending', 'in_flight']),
            ],
        )

    async def get_cross_chain_actions(self, agentId: str, limit: int = 20) -> list[CrossChainAction]:
        return await CrossChainActionsRepository.list_many(
            database=self.database,
            fieldFilters=[UUIDFieldFilter(fieldName='agentId', eq=agentId)],
            orders=[Order(fieldName='createdDate', direction=Direction.DESCENDING)],
            limit=limit,
        )

    async def update_cross_chain_action(
        self,
        crossChainActionId: int,
        status: str | None = None,
        txHash: str | None = None,
        bridgeName: str | None = None,
        details: dict[str, object] | None = None,
    ) -> CrossChainAction:
        kwargs: dict[str, object] = {'crossChainActionId': crossChainActionId}
        if status is not None:
            kwargs['status'] = status
        if txHash is not None:
            kwargs['txHash'] = txHash
        if bridgeName is not None:
            kwargs['bridgeName'] = bridgeName
        if details is not None:
            kwargs['details'] = details
        return await CrossChainActionsRepository.update(
            database=self.database,
            connection=None,
            **kwargs,
        )
