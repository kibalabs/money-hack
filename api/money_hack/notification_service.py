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

    async def send_auto_repay_success(
        self,
        agent: Agent,
        user: User,
        repayAmount: float,
        oldLtv: float,
        newLtv: float,
        isVaultWithdrawal: bool = True,
    ) -> bool:
        """Send notification when auto-repay is executed."""
        if not user.telegramChatId:
            return False
        sourceText = ' from your yield vault' if isVaultWithdrawal else ''
        message = f'I detected your LTV was high ({oldLtv:.1%}) and automatically withdrew ${repayAmount:.2f}{sourceText} to repay debt. Your position is now healthy at {newLtv:.1%}.'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='auto_repay_success', message=f'Auto-repay executed: ${repayAmount:.2f}. LTV {oldLtv:.1%} -> {newLtv:.1%}', success=success)
        return success

    async def send_auto_borrow_success(
        self,
        agent: Agent,
        user: User,
        borrowAmount: float,
        oldLtv: float,
        newLtv: float,
    ) -> bool:
        """Send notification when auto-borrow is executed to increase yield."""
        if not user.telegramChatId:
            return False
        message = f'Your LTV was low ({oldLtv:.1%}), so I borrowed an additional ${borrowAmount:.2f} USDC and deposited it into the yield vault to maximize your earnings. Your LTV is now {newLtv:.1%}, back on target.'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='auto_borrow_success', message=f'Auto-borrow executed: ${borrowAmount:.2f}. LTV {oldLtv:.1%} -> {newLtv:.1%}', success=success)
        return success

    async def send_auto_optimize_success(
        self,
        agent: Agent,
        user: User,
        borrowAmount: float,
        oldLtv: float,
        newLtv: float,
        priceContext: str | None = None,
    ) -> bool:
        """Send notification when auto-optimization (yield looping) is executed."""
        if not user.telegramChatId:
            return False
        message = f'Market conditions are favorable, so I borrowed an additional ${borrowAmount:.2f} USDC and deposited it into the yield vault to maximize your earnings. LTV moved from {oldLtv:.1%} to {newLtv:.1%}.'
        if priceContext:
            message += f'\n\nMarket: {priceContext}'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(
            agentId=agent.agentId,
            notificationType='auto_optimize_success',
            message=f'Auto-optimize executed: ${borrowAmount:.2f}. LTV {oldLtv:.1%} -> {newLtv:.1%}',
            success=success,
        )
        return success

    async def send_insufficient_vault_warning(
        self,
        agent: Agent,
        user: User,
        currentLtv: float,
        maxLtv: float,
        requiredAmount: float,
    ) -> bool:
        """Send warning when vault has insufficient funds for auto-repay (user withdrew USDC)."""
        if not user.telegramChatId:
            return False
        message = (
            f'⚠️ Your LTV is high ({currentLtv:.1%}, max: {maxLtv:.1%}) and I need ${requiredAmount:.2f} USDC to repay debt, '
            f'but your yield vault balance is too low. It looks like USDC has been withdrawn. '
            f'Please deposit more collateral or return USDC to restore your position health.'
        )
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='insufficient_vault_warning', message=f'Insufficient vault: need ${requiredAmount:.2f}, LTV {currentLtv:.1%}', success=success)
        return success

    async def send_daily_digest(
        self,
        agent: Agent,
        user: User,
        currentLtv: float,
        collateralValue: float,
        debtValue: float,
    ) -> bool:
        """Send daily digest notification."""
        if not user.telegramChatId:
            return False
        message = f'Daily Update: Everything is healthy. 🟢\nCurrent LTV: {currentLtv:.1%}\nCollateral: ${collateralValue:.2f}\nDebt: ${debtValue:.2f}\nNo action needed.'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='daily_digest', message='Daily digest sent.', success=success)
        return success

    async def send_cross_chain_failed(
        self,
        agent: Agent,
        user: User,
        actionId: int | None,
    ) -> bool:
        """Send notification when a cross-chain action fails."""
        if not user.telegramChatId:
            return False
        message = f'⚠️ A cross-chain bridge action (#{actionId}) has failed. Please check your position.'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='cross_chain_failed', message=f'Cross-chain action #{actionId} failed', success=success)
        return success

    async def send_cross_chain_withdraw_initiated(
        self,
        agent: Agent,
        user: User,
        amount: float,
        toChain: int,
        actionId: int | None,
    ) -> bool:
        """Send notification when a cross-chain withdrawal is initiated."""
        if not user.telegramChatId:
            return False
        chainNames = {1: 'Ethereum', 8453: 'Base', 42161: 'Arbitrum', 10: 'Optimism', 137: 'Polygon'}
        chainName = chainNames.get(toChain, f'Chain {toChain}')
        message = f'🌉 Cross-chain withdrawal initiated: ${amount:.2f} USDC → {chainName}. Bridge in progress (action #{actionId}).'
        success = await self.telegramClient.send_message(chatId=user.telegramChatId, text=message)
        await self._log_notification(agentId=agent.agentId, notificationType='cross_chain_withdraw', message=f'Cross-chain withdraw ${amount:.2f} to {chainName}', success=success)
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
