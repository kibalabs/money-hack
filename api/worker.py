import asyncio
import os

from core import logging
from core.notifications.discord_client import DiscordClient as CoreDiscordClient
from core.queues.message_queue_processor import MessageQueueProcessor
from core.util.value_holder import RequestIdHolder

from money_hack.app_message_processor import AppMessageProcessor
from money_hack.create_agent_manager import create_agent_manager

name = os.environ.get('NAME', 'borrowbot-api')
version = os.environ.get('VERSION', 'local')
environment = os.environ.get('ENV', 'dev')
isRunningDebugMode = environment == 'dev'
DISCORD_NOTIFICATIONS_DEV_WEBHOOK_URL = os.environ['DISCORD_NOTIFICATIONS_DEV_WEBHOOK_URL']

requestIdHolder = RequestIdHolder()
if isRunningDebugMode:
    logging.init_basic_logging()
else:
    logging.init_json_logging(name=name, version=version, environment=environment, requestIdHolder=requestIdHolder)
logging.init_external_loggers(loggerNames=['httpx'])


async def main() -> None:
    agentManager = create_agent_manager()
    coreDiscordClient = CoreDiscordClient(
        webhookUrl=DISCORD_NOTIFICATIONS_DEV_WEBHOOK_URL,
        requester=agentManager.requester,
    )
    messageProcessor = AppMessageProcessor(
        agentManager=agentManager,
        # database=agentManager.database,
    )
    workQueueProcessor = MessageQueueProcessor(
        queue=agentManager.workQueue,
        messageProcessor=messageProcessor,
        requestIdHolder=requestIdHolder,
        notificationClients=[
            coreDiscordClient,
        ],
    )

    await agentManager.workQueue.connect()
    await agentManager.userManager.database.connect(poolSize=2)
    try:
        await workQueueProcessor.run()
    finally:
        await agentManager.requester.close_connections()
        await agentManager.userManager.database.disconnect()
        await agentManager.workQueue.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
