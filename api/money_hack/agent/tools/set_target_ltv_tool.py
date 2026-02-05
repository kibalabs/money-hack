from pydantic import Field

from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.chat_tool import ChatToolInput
from money_hack.agent.runtime_state import RuntimeState


class SetTargetLtvInput(ChatToolInput):
    """Parameters for setting target LTV."""

    target_ltv: float = Field(description='The new target LTV as a decimal (e.g., 0.70 for 70%)')


class SetTargetLtvTool(ChatTool[SetTargetLtvInput, RuntimeState]):
    """Tool to change the user's target LTV preference."""

    def __init__(self) -> None:
        super().__init__(
            name='set_target_ltv',
            description="""Change the user's target LTV (Loan-to-Value) ratio. Valid values are between 0.50 (50%) and 0.80 (80%). Lower LTV is safer but earns less, higher LTV is riskier but earns more. Use this when the user wants to change their risk preference or adjust their target LTV.""",
            paramsSchema=SetTargetLtvInput,
        )

    async def execute_inner(self, runtimeState: RuntimeState, params: SetTargetLtvInput) -> str:
        if params.target_ltv < 0.50 or params.target_ltv > 0.80:  # noqa: PLR2004
            return f'Invalid target LTV: {params.target_ltv}. Target LTV must be between 0.50 (50%) and 0.80 (80%).'
        position = await runtimeState.databaseStore.get_position_by_agent(agentId=runtimeState.agentId)
        if position is None:
            return 'Cannot set target LTV: no active position found.'
        old_ltv = position.targetLtv
        await runtimeState.databaseStore.update_position(
            agentPositionId=position.agentPositionId,
            targetLtv=params.target_ltv,
        )
        await runtimeState.databaseStore.log_agent_action(
            agentId=runtimeState.agentId,
            actionType='ltv_change',
            value=f'{params.target_ltv * 100:.1f}%',
            valueId=None,
            details={
                'old_target_ltv': old_ltv,
                'new_target_ltv': params.target_ltv,
                'requested_by': 'user_chat',
            },
        )
        return f'Target LTV successfully changed from {old_ltv * 100:.1f}% to {params.target_ltv * 100:.1f}%. The agent will now aim to maintain this LTV ratio.'
