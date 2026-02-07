from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core import logging
from core.util import chain_util

from money_hack.api.v1_resources import TransactionCall
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.model import AgentPosition
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.morpho.transaction_builder import TransactionBuilder
from money_hack.store.database_store import DatabaseStore

if TYPE_CHECKING:
    from money_hack.blockchain_data.price_intelligence_service import PriceIntelligenceService
    from money_hack.forty_acres.forty_acres_client import FortyAcresClient

LTV_MARGIN_UPPER = 0.05
LTV_MARGIN_LOWER = 0.05
MIN_ACTION_VALUE_USD = 1.0
MIN_OPTIMIZE_ANNUAL_GAIN_USD = 100.0
VOLATILITY_THRESHOLD = 0.02  # 2% — suppress optimization if 1h change exceeds this


@dataclass
class LtvCheckResult:
    position_id: int
    agent_id: str
    current_ltv: float
    target_ltv: float
    max_ltv: float
    needs_action: bool
    action_type: str | None
    action_amount: int | None
    reason: str


@dataclass
class LtvActionTransactions:
    position_id: int
    action_type: str
    transactions: list[TransactionCall]
    repay_amount: int
    vault_withdraw_amount: int


class LtvManager:
    """Manages LTV monitoring and automatic adjustments for positions."""

    def __init__(
        self,
        chainId: int,
        usdcAddress: str,
        yoVaultAddress: str,
        morphoClient: MorphoClient,
        alchemyClient: AlchemyClient,
        databaseStore: DatabaseStore,
        priceIntelligenceService: PriceIntelligenceService | None = None,
        fortyAcresClient: FortyAcresClient | None = None,
    ) -> None:
        self.chainId = chainId
        self.usdcAddress = usdcAddress
        self.yoVaultAddress = yoVaultAddress
        self.morphoClient = morphoClient
        self.alchemyClient = alchemyClient
        self.databaseStore = databaseStore
        self.priceIntelligenceService = priceIntelligenceService
        self.fortyAcresClient = fortyAcresClient
        self.transactionBuilder = TransactionBuilder(chainId=chainId, usdcAddress=usdcAddress, yoVaultAddress=yoVaultAddress)

    async def _get_collateral_price(self, collateralAddress: str) -> float:
        priceData = await self.alchemyClient.get_asset_current_price(chainId=self.chainId, assetAddress=collateralAddress)
        return priceData.priceUsd

    async def check_position_ltv(
        self,
        position: AgentPosition,
        collateralDecimals: int = 18,
        onchainCollateral: int | None = None,
        onchainBorrow: int | None = None,
        onchainVaultAssets: int | None = None,
    ) -> LtvCheckResult:
        """Check if a position needs LTV adjustment.
        Requires onchainCollateral, onchainBorrow, and onchainVaultAssets from live on-chain data.
        """
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=position.collateralAsset)
        if market is None:
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=0,
                target_ltv=position.targetLtv,
                max_ltv=0,
                needs_action=False,
                action_type=None,
                action_amount=None,
                reason='Market not found',
            )
        try:
            collateralPriceUsd = await self._get_collateral_price(position.collateralAsset)
        except Exception as e:  # noqa: BLE001
            logging.warning(f'Failed to get collateral price for {position.collateralAsset}: {e}')
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=0,
                target_ltv=position.targetLtv,
                max_ltv=market.lltv,
                needs_action=False,
                action_type=None,
                action_amount=None,
                reason='Price fetch failed',
            )
        if onchainCollateral is None or onchainBorrow is None:
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=0,
                target_ltv=position.targetLtv,
                max_ltv=market.lltv,
                needs_action=False,
                action_type=None,
                action_amount=None,
                reason='On-chain position data not provided',
            )
        collateralRaw = onchainCollateral
        borrowRaw = onchainBorrow
        collateralAmountHuman = collateralRaw / (10**collateralDecimals)
        collateralValueUsd = collateralAmountHuman * collateralPriceUsd
        borrowValueUsd = borrowRaw / 1e6
        if collateralValueUsd <= 0:
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=0,
                target_ltv=position.targetLtv,
                max_ltv=market.lltv,
                needs_action=False,
                action_type=None,
                action_amount=None,
                reason='No collateral value',
            )
        currentLtv = borrowValueUsd / collateralValueUsd
        maxLtv = market.lltv
        upperThreshold = position.targetLtv + LTV_MARGIN_UPPER
        lowerThreshold = position.targetLtv - LTV_MARGIN_LOWER
        if currentLtv > upperThreshold:
            repayAmount = int((borrowValueUsd - position.targetLtv * collateralValueUsd) * 1e6)
            if repayAmount / 1e6 < MIN_ACTION_VALUE_USD:
                return LtvCheckResult(
                    position_id=position.agentPositionId,
                    agent_id=position.agentId,
                    current_ltv=currentLtv,
                    target_ltv=position.targetLtv,
                    max_ltv=maxLtv,
                    needs_action=False,
                    action_type=None,
                    action_amount=None,
                    reason=f'Repay amount ${repayAmount / 1e6:.2f} below minimum',
                )
            # Check if we have enough funds in the vault to auto-repay
            vaultBalance = onchainVaultAssets if onchainVaultAssets is not None else 0
            canAutoRepay = vaultBalance >= repayAmount
            actionType = 'auto_repay' if canAutoRepay else 'manual_repay'
            reason = f'LTV {currentLtv:.2%} exceeds upper threshold {upperThreshold:.2%}'
            if not canAutoRepay:
                reason += f'. Insufficient vault funds (${vaultBalance / 1e6:.2f} < ${repayAmount / 1e6:.2f})'

            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=currentLtv,
                target_ltv=position.targetLtv,
                max_ltv=maxLtv,
                needs_action=True,
                action_type=actionType,
                action_amount=repayAmount,
                reason=reason,
            )
        if currentLtv < lowerThreshold:
            borrowAmount = int((position.targetLtv * collateralValueUsd - borrowValueUsd) * 1e6)
            if borrowAmount / 1e6 < MIN_ACTION_VALUE_USD:
                return LtvCheckResult(
                    position_id=position.agentPositionId,
                    agent_id=position.agentId,
                    current_ltv=currentLtv,
                    target_ltv=position.targetLtv,
                    max_ltv=maxLtv,
                    needs_action=False,
                    action_type=None,
                    action_amount=None,
                    reason=f'Borrow amount ${borrowAmount / 1e6:.2f} below minimum',
                )
            # Auto-Optimizer gates: check profitability and volatility before borrowing more
            optimizeSuppressed, suppressReason = await self._check_optimize_gates(
                borrowAmountUsd=borrowAmount / 1e6,
                borrowApy=market.borrow_apy,
                collateralAddress=position.collateralAsset,
            )
            if optimizeSuppressed:
                return LtvCheckResult(
                    position_id=position.agentPositionId,
                    agent_id=position.agentId,
                    current_ltv=currentLtv,
                    target_ltv=position.targetLtv,
                    max_ltv=maxLtv,
                    needs_action=False,
                    action_type=None,
                    action_amount=None,
                    reason=suppressReason,
                )
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=currentLtv,
                target_ltv=position.targetLtv,
                max_ltv=maxLtv,
                needs_action=True,
                action_type='auto_optimize',
                action_amount=borrowAmount,
                reason=f'LTV {currentLtv:.2%} below lower threshold {lowerThreshold:.2%}',
            )
        return LtvCheckResult(
            position_id=position.agentPositionId,
            agent_id=position.agentId,
            current_ltv=currentLtv,
            target_ltv=position.targetLtv,
            max_ltv=maxLtv,
            needs_action=False,
            action_type=None,
            action_amount=None,
            reason=f'LTV {currentLtv:.2%} within acceptable range',
        )

    async def _check_optimize_gates(self, borrowAmountUsd: float, borrowApy: float, collateralAddress: str) -> tuple[bool, str]:
        """Check profitability and volatility gates before auto-optimizing. Returns (suppressed, reason)."""
        # Gate 1: Profitability — yield must exceed borrow cost
        if self.fortyAcresClient:
            try:
                yieldApy = await self.fortyAcresClient.get_yield_apy(chainId=self.chainId)
                if yieldApy is not None:
                    spread = yieldApy - borrowApy
                    if spread <= 0:
                        return True, f'Optimization suppressed: negative spread (yield {yieldApy:.2%} - borrow {borrowApy:.2%} = {spread:.2%})'
                    projectedAnnualGain = borrowAmountUsd * spread
                    if projectedAnnualGain < MIN_OPTIMIZE_ANNUAL_GAIN_USD:
                        return True, f'Optimization suppressed: projected annual gain ${projectedAnnualGain:.2f} below ${MIN_OPTIMIZE_ANNUAL_GAIN_USD:.0f} minimum'
            except Exception as e:  # noqa: BLE001
                logging.warning(f'Failed to check yield APY for optimization gate: {e}')

        # Gate 2: Volatility — suppress if price is moving too fast
        if self.priceIntelligenceService:
            try:
                priceAnalysis = await self.priceIntelligenceService.get_price_analysis(chainId=self.chainId, assetAddress=collateralAddress)
                if priceAnalysis.is_volatile(threshold=VOLATILITY_THRESHOLD):
                    return True, (
                        f'Optimization suppressed: high volatility '
                        f'(1h change: {priceAnalysis.change_1h_pct:+.2%}, '
                        f'24h vol: {priceAnalysis.volatility_24h:.2%})'
                    )
            except Exception as e:  # noqa: BLE001
                logging.warning(f'Failed to check price volatility for optimization gate: {e}')

        return False, ''

    async def build_auto_repay_transactions(self, position: AgentPosition, repayAmount: int, userAddress: str) -> LtvActionTransactions:
        """Build transactions to auto-repay debt (withdraw from vault, repay to Morpho)."""
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=position.collateralAsset)
        if market is None:
            raise ValueError(f'No market found for collateral {position.collateralAsset}')
        normalizedAddress = chain_util.normalize_address(userAddress)
        vaultWithdrawAmount = repayAmount
        transactions = self.transactionBuilder.build_partial_repay_transactions_from_market(
            user_address=normalizedAddress,
            collateral_address=position.collateralAsset,
            repay_amount=repayAmount,
            vault_withdraw_amount=vaultWithdrawAmount,
            market=market,
            needs_usdc_approval=True,
        )
        return LtvActionTransactions(
            position_id=position.agentPositionId,
            action_type='auto_repay',
            transactions=transactions,
            repay_amount=repayAmount,
            vault_withdraw_amount=vaultWithdrawAmount,
        )

    async def build_auto_borrow_transactions(self, position: AgentPosition, borrowAmount: int, userAddress: str) -> LtvActionTransactions:
        """Build transactions to auto-borrow more USDC and deposit to vault."""
        market = await self.morphoClient.get_market(chain_id=self.chainId, collateral_address=position.collateralAsset)
        if market is None:
            raise ValueError(f'No market found for collateral {position.collateralAsset}')
        normalizedAddress = chain_util.normalize_address(userAddress)
        transactions = self.transactionBuilder.build_auto_borrow_transactions_from_market(
            user_address=normalizedAddress,
            collateral_address=position.collateralAsset,
            borrow_amount=borrowAmount,
            market=market,
            needs_usdc_approval=True,
        )
        return LtvActionTransactions(
            position_id=position.agentPositionId,
            action_type='auto_borrow',
            transactions=transactions,
            repay_amount=0,
            vault_withdraw_amount=0,
        )

    async def log_ltv_check(self, result: LtvCheckResult) -> None:
        """Log an LTV check result as an agent action."""
        await self.databaseStore.log_agent_action(
            agentId=result.agent_id,
            actionType='ltv_check',
            value=result.action_type or 'no_action',
            valueId=str(result.position_id),
            details={
                'current_ltv': result.current_ltv,
                'target_ltv': result.target_ltv,
                'max_ltv': result.max_ltv,
                'needs_action': result.needs_action,
                'action_amount': result.action_amount,
                'reason': result.reason,
            },
        )
