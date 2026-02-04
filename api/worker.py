import asyncio
import os

from core import logging
from core.util.value_holder import RequestIdHolder

from money_hack import constants
from money_hack.create_agent_manager import create_agent_manager
from money_hack.morpho.ltv_manager import LtvManager
from money_hack.notification_service import NotificationService

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

LTV_CHECK_INTERVAL_SECONDS = 300
YO_VAULT_ADDRESS = '0x0000000f2eB9f69274678c76222B35eEc7588a65'
CRITICAL_LTV_THRESHOLD = 0.80


async def monitor_positions(ltvManager: LtvManager, notificationService: NotificationService) -> None:
    while True:
        try:
            positions = await ltvManager.databaseStore.get_all_active_positions()
            logging.info(f'Checking LTV for {len(positions)} active positions')
            for position in positions:
                try:
                    result = await ltvManager.check_position_ltv(position)
                    await ltvManager.log_ltv_check(result)
                    if result.current_ltv >= CRITICAL_LTV_THRESHOLD * result.max_ltv and result.max_ltv > 0:
                        agent = await ltvManager.databaseStore.get_agent(agentId=position.agentId)
                        if agent is not None:
                            user = await ltvManager.databaseStore.get_user(userId=agent.userId)
                            if user is not None:
                                await notificationService.send_critical_ltv_warning(
                                    agent=agent,
                                    user=user,
                                    currentLtv=result.current_ltv,
                                    maxLtv=result.max_ltv,
                                )
                    if result.needs_action:
                        logging.warning(f'Position {position.agentPositionId} needs action: {result.action_type} - {result.reason}')
                    else:
                        logging.debug(f'Position {position.agentPositionId}: {result.reason}')
                except Exception:  # noqa: BLE001
                    logging.exception(f'Error checking position {position.agentPositionId}')
        except Exception:  # noqa: BLE001
            logging.exception('Error in position monitoring loop')
        await asyncio.sleep(LTV_CHECK_INTERVAL_SECONDS)


async def main() -> None:
    agentManager = create_agent_manager()
    chainId = agentManager.chainId
    usdcAddress = constants.CHAIN_USDC_MAP.get(chainId)
    if usdcAddress is None:
        raise ValueError(f'USDC not supported on chain {chainId}')
    ltvManager = LtvManager(
        chainId=chainId,
        usdcAddress=usdcAddress,
        yoVaultAddress=YO_VAULT_ADDRESS,
        morphoClient=agentManager.morphoClient,
        alchemyClient=agentManager.alchemyClient,
        databaseStore=agentManager.databaseStore,
    )
    notificationService = NotificationService(
        telegramClient=agentManager.telegramClient,
        databaseStore=agentManager.databaseStore,
    )
    logging.info('Worker started, beginning LTV monitoring...')
    try:
        await monitor_positions(ltvManager, notificationService)
    finally:
        await agentManager.requester.close_connections()


if __name__ == '__main__':
    asyncio.run(main())
