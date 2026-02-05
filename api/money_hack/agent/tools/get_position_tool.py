from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.chat_tool import ChatToolInput
from money_hack.agent.runtime_state import RuntimeState


class GetPositionInput(ChatToolInput):
    """No parameters needed - gets the user's current position."""


class GetPositionTool(ChatTool[GetPositionInput, RuntimeState]):
    """Tool to get the user's current lending position details."""

    def __init__(self) -> None:
        super().__init__(
            name='get_position',
            description="""Get the user's current lending position including collateral amount, collateral value, borrowed amount, current LTV, target LTV, health factor, vault balance, and accrued yield. Use this when the user asks about their position, holdings, balance, LTV, or health status.""",
            paramsSchema=GetPositionInput,
        )

    async def execute_inner(self, runtimeState: RuntimeState, params: GetPositionInput) -> str:  # noqa: ARG002
        position = await runtimeState.agentManager.get_position(user_address=runtimeState.walletAddress)
        if position is None:
            return 'The user does not have an active lending position.'
        position_data = {
            'position_id': position.position_id,
            'collateral': {
                'asset': position.collateral_asset.symbol,
                'amount': f'{int(position.collateral_amount) / (10**position.collateral_asset.decimals):.6f}',
                'value_usd': f'${position.collateral_value_usd:,.2f}',
            },
            'borrow': {
                'asset': 'USDC',
                'amount': f'{int(position.borrow_amount) / 1e6:,.2f}',
                'value_usd': f'${position.borrow_value_usd:,.2f}',
            },
            'ltv': {
                'current': f'{position.current_ltv * 100:.1f}%',
                'target': f'{position.target_ltv * 100:.1f}%',
            },
            'health_factor': f'{position.health_factor:.2f}',
            'vault_balance': {
                'shares': position.vault_balance,
                'value_usd': f'${position.vault_balance_usd:,.2f}',
            },
            'yield': {
                'accrued': position.accrued_yield,
                'accrued_usd': f'${position.accrued_yield_usd:,.2f}',
                'estimated_apy': f'{position.estimated_apy * 100:.2f}%',
            },
            'status': position.status,
        }
        return f"The user's current position:\n{self.data_to_markdown_yaml(position_data)}"
