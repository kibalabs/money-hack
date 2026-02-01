from core.exceptions import KibaException
from core.queues.message_queue_processor import MessageProcessor
from core.queues.model import Message

from money_hack.agent_manager import AgentManager


class AppMessageProcessor(MessageProcessor):
    def __init__(self, agentManager: AgentManager) -> None:
        self.agentManager = agentManager

    async def process_message(self, message: Message) -> None:  # noqa: ARG002
        # async with self.database.create_context_connection():
        # if message.command == PostOptionsToTwitterMessageContent.get_command():
        #     postOptionsToTwitterMessageContent = PostOptionsToTwitterMessageContent.model_validate(message.content)
        #     await self.agentManager.post_options_to_twitter()
        #     return
        raise KibaException(message='Message was unhandled')
