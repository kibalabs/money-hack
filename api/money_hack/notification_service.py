from core import logging

from money_hack.external.telegram_client import TelegramClient
from money_hack.model import Agent
from money_hack.model import User
from money_hack.store.database_store import DatabaseStore


class NotificationService:
    """Service for sending Telegram notifications and logging them."""

    def __init__(self, telegramClient: TelegramClient, databaseStore: DatabaseStore) -> None:
        self.telegramClient = telegramClient
        self.databaseStore = databaseStore

    async def _log_notification(self, agentId: str, notificationType: str, message: str, success: bool) -> None:
        """Log notification to tbl_agent_actions."""
        await self.databaseStore.log_agent_action(
            agentId=agentId,
            actionType='notification',
            value=notificationType,
            valueId=None,
            details={'message': message, 'success': success},
        )

    async def send_position_opened(
        self,
        agent: Agent,
        user: User,
        collateralSymbol: str,
        collateralAmount: str,
        borrowAmount: str,
        ltv: float,
    ) -> bool:
        """Send notification when a position is opened."""
        if not user.telegramChatId:
            logging.debug(f'User {user.userId} has no telegram chat ID, skipping notification')
            return False
        success = await self.telegramClient.send_position_opened_notification(
            chatId=user.telegramChatId,
            agentName=agent.name,
            agentEmoji=agent.emoji,
            collateralSymbol=collateralSymbol,
            collateralAmount=collateralAmount,
            borrowAmount=borrowAmount,
            ltv=ltv,
        )
        await self._log_notification(
            agentId=agent.agentId,
            notificationType='position_opened',
            message=f'Position opened: {collateralAmount} {collateralSymbol}, ${borrowAmount} USDC, LTV {ltv:.1%}',
            success=success,
        )
        return success

    async def send_ltv_adjustment(
        self,
        agent: Agent,
        user: User,
        actionType: str,
        amount: str,
        oldLtv: float,
        newLtv: float,
    ) -> bool:
        """Send notification when LTV is adjusted."""
        if not user.telegramChatId:
            logging.debug(f'User {user.userId} has no telegram chat ID, skipping notification')
            return False
        success = await self.telegramClient.send_ltv_adjustment_notification(
            chatId=user.telegramChatId,
            agentName=agent.name,
            agentEmoji=agent.emoji,
            actionType=actionType,
            amount=amount,
            oldLtv=oldLtv,
            newLtv=newLtv,
        )
        await self._log_notification(
            agentId=agent.agentId,
            notificationType='ltv_adjustment',
            message=f'LTV adjustment ({actionType}): ${amount} USDC, {oldLtv:.1%} -> {newLtv:.1%}',
            success=success,
        )
        return success

    async def send_critical_ltv_warning(
        self,
        agent: Agent,
        user: User,
        currentLtv: float,
        maxLtv: float,
    ) -> bool:
        """Send critical LTV warning notification."""
        if not user.telegramChatId:
            logging.debug(f'User {user.userId} has no telegram chat ID, skipping notification')
            return False
        success = await self.telegramClient.send_critical_ltv_warning(
            chatId=user.telegramChatId,
            agentName=agent.name,
            agentEmoji=agent.emoji,
            currentLtv=currentLtv,
            maxLtv=maxLtv,
        )
        await self._log_notification(
            agentId=agent.agentId,
            notificationType='critical_ltv_warning',
            message=f'Critical LTV warning: {currentLtv:.1%} (max: {maxLtv:.1%})',
            success=success,
        )
        return success

    async def send_position_closed(
        self,
        agent: Agent,
        user: User,
        collateralReturned: str,
        collateralSymbol: str,
        totalYieldEarned: str,
    ) -> bool:
        """Send notification when a position is closed."""
        if not user.telegramChatId:
            logging.debug(f'User {user.userId} has no telegram chat ID, skipping notification')
            return False
        success = await self.telegramClient.send_position_closed_notification(
            chatId=user.telegramChatId,
            agentName=agent.name,
            agentEmoji=agent.emoji,
            collateralReturned=collateralReturned,
            collateralSymbol=collateralSymbol,
            totalYieldEarned=totalYieldEarned,
        )
        await self._log_notification(
            agentId=agent.agentId,
            notificationType='position_closed',
            message=f'Position closed: {collateralReturned} {collateralSymbol}, yield earned: ${totalYieldEarned}',
            success=success,
        )
        return success
