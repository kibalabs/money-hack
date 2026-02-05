from pydantic import Field

from money_hack.agent.chat_tool import ChatTool
from money_hack.agent.chat_tool import ChatToolInput
from money_hack.agent.runtime_state import RuntimeState


class GetActionHistoryInput(ChatToolInput):
    """Parameters for getting action history."""

    limit: int = Field(default=10, description='Maximum number of actions to return (default 10)')


class GetActionHistoryTool(ChatTool[GetActionHistoryInput, RuntimeState]):
    """Tool to get the agent's recent action history."""

    def __init__(self) -> None:
        super().__init__(
            name='get_action_history',
            description="""Get the recent actions taken by the agent including LTV adjustments, auto-repays, auto-borrows, and position changes. Use this when the user asks about what the agent has been doing, why an action was taken, or wants to see a history of changes.""",
            paramsSchema=GetActionHistoryInput,
        )

    async def execute_inner(self, runtimeState: RuntimeState, params: GetActionHistoryInput) -> str:
        actions = await runtimeState.databaseStore.get_agent_actions(
            agentId=runtimeState.agentId,
            limit=params.limit,
        )
        if not actions:
            return 'No actions have been recorded for this agent yet.'
        action_list = [
            {
                'date': action.createdDate.strftime('%Y-%m-%d %H:%M UTC'),
                'type': action.actionType,
                'value': action.value,
                'details': action.details,
            }
            for action in actions
        ]
        return f'Recent agent actions:\n{self.data_to_markdown_yaml(action_list)}'
