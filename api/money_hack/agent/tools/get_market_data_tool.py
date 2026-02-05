from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.chat_tool import ChatToolInput
from money_hack.agent.runtime_state import RuntimeState


class GetMarketDataInput(ChatToolInput):
    """No parameters needed - gets current market data."""


class GetMarketDataTool(ChatTool[GetMarketDataInput, RuntimeState]):
    """Tool to get current market data including borrow APY, yield APY, and prices."""

    def __init__(self) -> None:
        super().__init__(
            name='get_market_data',
            description="""Get current market data including borrow APY rates for each collateral type, yield vault APY, and spread between yield and borrow. Use this when the user asks about rates, APY, market conditions, or profitability.""",
            paramsSchema=GetMarketDataInput,
        )

    async def execute_inner(self, runtimeState: RuntimeState, params: GetMarketDataInput) -> str:  # noqa: ARG002
        collateralMarkets, yieldApy, vaultAddress, vaultName = await runtimeState.agentManager.get_market_data()
        market_data = {
            'yield_vault': {
                'name': vaultName,
                'address': vaultAddress,
                'apy': f'{yieldApy * 100:.2f}%',
            },
            'collateral_markets': [
                {
                    'collateral': market.collateral_symbol,
                    'borrow_apy': f'{market.borrow_apy * 100:.2f}%',
                    'max_ltv': f'{market.max_ltv * 100:.1f}%',
                    'spread': f'{(yieldApy - market.borrow_apy) * 100:.2f}%',
                }
                for market in collateralMarkets
            ],
        }
        return f'Current market data:\n{self.data_to_markdown_yaml(market_data)}'
