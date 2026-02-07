from pydantic import Field

from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.chat_tool import ChatToolInput
from money_hack.agent.runtime_state import RuntimeState


class GetPriceAnalysisInput(ChatToolInput):
    """Parameters for price analysis."""

    asset: str = Field(description="Asset symbol to analyze: 'WETH' or 'cbBTC'")


class GetPriceAnalysisTool(ChatTool[GetPriceAnalysisInput, RuntimeState]):
    """Tool to get historical price analysis for a collateral asset."""

    def __init__(self) -> None:
        super().__init__(
            name='get_price_analysis',
            description="""Get historical price analysis for a collateral asset (WETH or cbBTC). Returns current price, 1h/24h/7d price changes, volatility, and trend direction. Use this when the user asks about price movements, volatility, market conditions, or when explaining rebalancing decisions.""",
            paramsSchema=GetPriceAnalysisInput,
        )

    async def execute_inner(self, runtimeState: RuntimeState, params: GetPriceAnalysisInput) -> str:
        if runtimeState.getPriceAnalysis is None:
            return 'Price analysis is not available at this time.'
        analysis = await runtimeState.getPriceAnalysis(params.asset)
        if analysis is None:
            return f'No price data available for {params.asset}. Valid assets are WETH and cbBTC.'
        price_data = {
            'asset': params.asset,
            'current_price': f'${analysis.current_price_usd:,.2f}',
            'changes': {
                '1h': f'{analysis.change_1h_pct:+.2%}',
                '24h': f'{analysis.change_24h_pct:+.2%}',
                '7d': f'{analysis.change_7d_pct:+.2%}',
            },
            'volatility_24h': f'{analysis.volatility_24h:.2%}',
            'trend': analysis.trend,
            'high_volatility': analysis.is_volatile(),
        }
        return f'Price analysis for {params.asset}:\n{self.data_to_markdown_yaml(price_data)}'
