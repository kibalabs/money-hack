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
    await agentManager.databaseStore.database.connect(poolSize=2)
    logging.info('Worker started, beginning AgentManager monitoring loop...')
    
    # Demo mode: More frequent checks and status notifications
    if isRunningDebugMode:
        logging.info('🎬 DEMO MODE: Enabling frequent status notifications')
        LTV_CHECK_INTERVAL_SECONDS = 180  # 3 minutes in demo mode
    else:
        LTV_CHECK_INTERVAL_SECONDS = 300  # 5 minutes in production
    
    iteration = 0
    try:
        while True:
            try:
                async with agentManager.databaseStore.database.create_context_connection():
                    await agentManager.check_positions_once()
                    
                    # Demo mode: Send periodic status updates even when no action is needed
                    if isRunningDebugMode and iteration % 2 == 0:  # Every other iteration (every 6 minutes)
                        await agentManager.send_demo_status_notifications()
                    
                iteration += 1
            except Exception:  # noqa: BLE001
                logging.exception('Error in position monitoring loop')
            await asyncio.sleep(LTV_CHECK_INTERVAL_SECONDS)
    finally:
        await agentManager.requester.close_connections()
        await agentManager.databaseStore.database.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
