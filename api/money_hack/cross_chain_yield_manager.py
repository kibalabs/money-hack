from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core import logging

if TYPE_CHECKING:
    from money_hack.external.lifi_client import LiFiClient
    from money_hack.store.database_store import DatabaseStore

BASE_CHAIN_ID = 8453
BASE_USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
MIN_CROSS_CHAIN_AMOUNT_USD = 10.0


@dataclass
class CrossChainResult:
    success: bool
    action_id: int | None
    amount: str
    from_chain: int
    to_chain: int
    reason: str


@dataclass
class CrossChainStatusResult:
    action_id: int
    old_status: str
    new_status: str
    is_complete: bool


class CrossChainManager:
    """Manages cross-chain deposits and withdrawals via LI.FI Composer.

    Deposits: User-initiated via LI.FI Widget (any chain → Base agent wallet).
    Withdrawals: Agent-executed on Base via LI.FI Composer (Base USDC → any chain).
    All agent transactions are on Base, gas paid by Coinbase Paymaster.
    """

    def __init__(
        self,
        lifiClient: LiFiClient,
        databaseStore: DatabaseStore,
    ) -> None:
        self.lifiClient = lifiClient
        self.databaseStore = databaseStore

    async def record_cross_chain_deposit(
        self,
        agentId: str,
        fromChain: int,
        fromToken: str,
        toToken: str,
        amount: str,
        txHash: str | None = None,
        bridgeName: str | None = None,
    ) -> CrossChainResult:
        """Record a user-initiated cross-chain deposit (any chain → Base).

        The actual bridging is handled by the LI.FI Widget on the frontend.
        This method just tracks the action in the database.
        """
        try:
            action = await self.databaseStore.create_cross_chain_action(
                agentId=agentId,
                actionType='deposit',
                fromChain=fromChain,
                toChain=BASE_CHAIN_ID,
                fromToken=fromToken,
                toToken=toToken,
                amount=amount,
                txHash=txHash,
                bridgeName=bridgeName,
                status='in_flight' if txHash else 'pending',
                details={
                    'direction': 'inbound',
                    'source': 'lifi_widget',
                },
            )
            logging.info(f'Cross-chain deposit recorded for agent {agentId}: chain {fromChain} → Base, amount={amount}')
            return CrossChainResult(
                success=True,
                action_id=action.crossChainActionId,
                amount=amount,
                from_chain=fromChain,
                to_chain=BASE_CHAIN_ID,
                reason='Deposit recorded',
            )
        except Exception as e:
            logging.exception(f'Failed to record cross-chain deposit: {e}')
            return CrossChainResult(
                success=False, action_id=None, amount=amount,
                from_chain=fromChain, to_chain=BASE_CHAIN_ID,
                reason=f'Failed to record: {e}',
            )

    async def prepare_cross_chain_withdrawal(
        self,
        agentId: str,
        agentWalletAddress: str,
        usdcAmount: int,
        toChain: int,
        toToken: str,
        toAddress: str,
    ) -> CrossChainResult:
        """Prepare a cross-chain withdrawal: get LI.FI quote for Base USDC → destination chain.

        Returns the quote details so the caller can execute the tx via the agent's smart wallet.
        The actual execution (approve + bridge tx) is done by agent_manager using _send_user_operation.
        """
        if usdcAmount / 1e6 < MIN_CROSS_CHAIN_AMOUNT_USD:
            return CrossChainResult(
                success=False, action_id=None, amount=str(usdcAmount),
                from_chain=BASE_CHAIN_ID, to_chain=toChain,
                reason=f'Amount ${usdcAmount / 1e6:.2f} below minimum ${MIN_CROSS_CHAIN_AMOUNT_USD}',
            )
        pending = await self.databaseStore.get_pending_cross_chain_actions(agentId=agentId)
        pendingWithdrawals = [a for a in pending if a.actionType == 'withdraw']
        if pendingWithdrawals:
            return CrossChainResult(
                success=False, action_id=None, amount=str(usdcAmount),
                from_chain=BASE_CHAIN_ID, to_chain=toChain,
                reason=f'Existing in-flight withdrawal ({len(pendingWithdrawals)} pending)',
            )
        try:
            quote = await self.lifiClient.get_quote(
                fromChain=BASE_CHAIN_ID,
                toChain=toChain,
                fromToken=BASE_USDC_ADDRESS,
                toToken=toToken,
                fromAmount=str(usdcAmount),
                fromAddress=agentWalletAddress,
                toAddress=toAddress,
            )
            action = await self.databaseStore.create_cross_chain_action(
                agentId=agentId,
                actionType='withdraw',
                fromChain=BASE_CHAIN_ID,
                toChain=toChain,
                fromToken=BASE_USDC_ADDRESS,
                toToken=toToken,
                amount=str(usdcAmount),
                txHash=None,
                bridgeName=quote.tool,
                status='pending',
                details={
                    'direction': 'outbound',
                    'to_address': toAddress,
                    'quote_tool': quote.tool,
                    'estimated_to_amount': quote.estimate.toAmount,
                    'estimated_to_amount_min': quote.estimate.toAmountMin,
                    'approval_address': quote.estimate.approvalAddress,
                    'tx_to': quote.transactionRequest.to,
                    'tx_data': quote.transactionRequest.data,
                    'tx_value': quote.transactionRequest.value,
                    'tx_gas_limit': quote.transactionRequest.gasLimit,
                },
            )
            logging.info(f'Cross-chain withdrawal prepared for agent {agentId}: ${usdcAmount / 1e6:.2f} USDC → chain {toChain} via {quote.tool}')
            return CrossChainResult(
                success=True,
                action_id=action.crossChainActionId,
                amount=str(usdcAmount),
                from_chain=BASE_CHAIN_ID,
                to_chain=toChain,
                reason=f'Quote obtained via {quote.tool}, estimated output: {quote.estimate.toAmount}',
            )
        except Exception as e:
            logging.exception(f'Failed to get LI.FI quote for cross-chain withdrawal: {e}')
            return CrossChainResult(
                success=False, action_id=None, amount=str(usdcAmount),
                from_chain=BASE_CHAIN_ID, to_chain=toChain,
                reason=f'LI.FI quote failed: {e}',
            )

    async def check_pending_actions(self, agentId: str) -> list[CrossChainStatusResult]:
        """Poll LI.FI status for all pending cross-chain actions."""
        pending = await self.databaseStore.get_pending_cross_chain_actions(agentId=agentId)
        results: list[CrossChainStatusResult] = []
        for action in pending:
            if not action.txHash:
                continue
            try:
                status = await self.lifiClient.get_status(
                    bridge=action.bridgeName or '',
                    fromChain=action.fromChain,
                    toChain=action.toChain,
                    txHash=action.txHash,
                )
                newStatus = action.status
                if status.status == 'DONE':
                    newStatus = 'completed'
                elif status.status == 'FAILED':
                    newStatus = 'failed'
                elif status.status in ('PENDING', 'NOT_FOUND'):
                    newStatus = 'in_flight'
                if newStatus != action.status:
                    await self.databaseStore.update_cross_chain_action(
                        crossChainActionId=action.crossChainActionId,
                        status=newStatus,
                        details={
                            **action.details,
                            'lifi_status': status.status,
                            'lifi_substatus': status.substatus,
                        },
                    )
                    logging.info(f'Cross-chain action {action.crossChainActionId} status: {action.status} -> {newStatus}')
                results.append(CrossChainStatusResult(
                    action_id=action.crossChainActionId,
                    old_status=action.status,
                    new_status=newStatus,
                    is_complete=newStatus in ('completed', 'failed'),
                ))
            except Exception:
                logging.exception(f'Failed to check status for cross-chain action {action.crossChainActionId}')
        return results
