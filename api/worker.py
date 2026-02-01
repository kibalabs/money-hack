import asyncio
import os

from core import logging
from core.util.value_holder import RequestIdHolder

from money_hack.create_agent_manager import create_agent_manager

name = os.environ.get('NAME', 'money-hack-worker')
version = os.environ.get('VERSION', 'local')
environment = os.environ.get('ENV', 'dev')
isRunningDebugMode = environment == 'dev'

requestIdHolder = RequestIdHolder()
if isRunningDebugMode:
    logging.init_basic_logging()
else:
    logging.init_json_logging(name=name, version=version, environment=environment, requestIdHolder=requestIdHolder)
logging.init_external_loggers(loggerNames=['httpx'])


async def main() -> None:
    agentManager = create_agent_manager()
    shutdownEvent = asyncio.Event()
    try:
        # TODO(krishan711): Implement worker logic for monitoring LTV and adjusting positions
        logging.info('Worker started, waiting for tasks...')
        await shutdownEvent.wait()
    finally:
        await agentManager.requester.close_connections()


if __name__ == '__main__':
    asyncio.run(main())
