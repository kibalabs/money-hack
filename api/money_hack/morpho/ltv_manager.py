from dataclasses import dataclass

from core import logging
from core.util import chain_util

from money_hack.api.v1_resources import TransactionCall
from money_hack.blockchain_data.alchemy_client import AlchemyClient
from money_hack.model import AgentPosition
from money_hack.morpho.morpho_client import MorphoClient
from money_hack.morpho.transaction_builder import TransactionBuilder
from money_hack.store.database_store import DatabaseStore

LTV_MARGIN_UPPER = 0.05
LTV_MARGIN_LOWER = 0.05
MIN_ACTION_VALUE_USD = 1.0


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
    ) -> None:
        self.chainId = chainId
        self.usdcAddress = usdcAddress
        self.yoVaultAddress = yoVaultAddress
        self.morphoClient = morphoClient
        self.alchemyClient = alchemyClient
        self.databaseStore = databaseStore
        self.transactionBuilder = TransactionBuilder(chainId=chainId, usdcAddress=usdcAddress, yoVaultAddress=yoVaultAddress)

    async def _get_collateral_price(self, collateralAddress: str) -> float:
        priceData = await self.alchemyClient.get_asset_current_price(chainId=self.chainId, assetAddress=collateralAddress)
        return priceData.priceUsd

    async def check_position_ltv(self, position: AgentPosition, collateralDecimals: int = 18) -> LtvCheckResult:
        """Check if a position needs LTV adjustment."""
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
        collateralAmountHuman = position.collateralAmount / (10**collateralDecimals)
        collateralValueUsd = collateralAmountHuman * collateralPriceUsd
        borrowValueUsd = position.borrowAmount / 1e6
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
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=currentLtv,
                target_ltv=position.targetLtv,
                max_ltv=maxLtv,
                needs_action=True,
                action_type='auto_repay',
                action_amount=repayAmount,
                reason=f'LTV {currentLtv:.2%} exceeds upper threshold {upperThreshold:.2%}',
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
            return LtvCheckResult(
                position_id=position.agentPositionId,
                agent_id=position.agentId,
                current_ltv=currentLtv,
                target_ltv=position.targetLtv,
                max_ltv=maxLtv,
                needs_action=True,
                action_type='auto_borrow',
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
