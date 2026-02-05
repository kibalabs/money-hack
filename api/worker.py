import asyncio
import datetime
import os

from core import logging
from core.util.value_holder import RequestIdHolder
from core.web3.eth_client import EncodedCall
from hexbytes import HexBytes

from money_hack import constants
from money_hack.agent_manager import AgentManager
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
WARN_INTERVAL_HOURS = 4
URGENT_INTERVAL_HOURS = 1


async def monitor_positions(ltvManager: LtvManager, notificationService: NotificationService, agentManager: AgentManager) -> None:
    while True:
        try:
            positions = await ltvManager.databaseStore.get_all_active_positions()
            logging.info(f'Checking LTV for {len(positions)} active positions')
            for position in positions:
                try:
                    result = await ltvManager.check_position_ltv(position)
                    await ltvManager.log_ltv_check(result)

                    agent = await ltvManager.databaseStore.get_agent(agentId=position.agentId)
                    if not agent:
                        continue
                    user = await ltvManager.databaseStore.get_user(userId=agent.userId)
                    if not user:
                        continue

                    # Handle Action
                    if result.needs_action and result.action_type == 'auto_repay':
                        logging.info(f'Position {position.agentPositionId}: Auto-repaying {result.action_amount} USDC')
                        try:
                            actionTx = await ltvManager.build_auto_repay_transactions(
                                position=position,
                                repayAmount=result.action_amount,
                                userAddress=agent.walletAddress,
                            )
                            calls = [EncodedCall(to=tx.toAddress, data=HexBytes(tx.data), value=int(tx.value)) for tx in actionTx.transactions]
                            # Using internal method as worker is part of backend service
                            await agentManager._send_user_operation(  # noqa: SLF001
                                agentWalletAddress=agent.walletAddress,
                                calls=calls,
                            )
                            await notificationService.send_auto_repay_success(
                                agent=agent,
                                user=user,
                                repayAmount=float(result.action_amount) / 1e6,  # Assuming 6 decimals for USDC
                                oldLtv=result.current_ltv,
                                newLtv=result.target_ltv,  # Approximate new LTV
                            )
                        except Exception:  # noqa: BLE001
                            logging.exception(f'Failed to auto-repay for position {position.agentPositionId}')
                            # Fallback to warning handled below if condition persists next check

                    # Handle Warnings (Manual Repay or Critical Threshold)
                    currentLtv = result.current_ltv
                    maxLtv = result.max_ltv
                    isCritical = currentLtv >= CRITICAL_LTV_THRESHOLD * maxLtv and maxLtv > 0
                    if (result.needs_action and result.action_type == 'manual_repay') or isCritical:
                        lastWarning = await ltvManager.databaseStore.get_latest_action_by_type(agent.agentId, 'critical_ltv_warning')
                        shouldWarn = True
                        if lastWarning:
                            timeSince = datetime.datetime.now(datetime.UTC) - lastWarning.createdDate.replace(tzinfo=datetime.UTC)
                            interval = URGENT_INTERVAL_HOURS if isCritical else WARN_INTERVAL_HOURS
                            if timeSince.total_seconds() < interval * 3600:
                                shouldWarn = False

                        if shouldWarn:
                            await notificationService.send_critical_ltv_warning(
                                agent=agent,
                                user=user,
                                currentLtv=currentLtv,
                                maxLtv=maxLtv,
                            )
                    elif result.needs_action:
                        logging.warning(f'Position {position.agentPositionId} needs action: {result.action_type} - {result.reason}')

                    # Daily Digest
                    lastDigest = await ltvManager.databaseStore.get_latest_action_by_type(agent.agentId, 'daily_digest')
                    shouldSendDigest = True
                    if lastDigest:
                        timeSince = datetime.datetime.now(datetime.UTC) - lastDigest.createdDate.replace(tzinfo=datetime.UTC)
                        if timeSince.total_seconds() < 24 * 3600:
                            shouldSendDigest = False

                    if shouldSendDigest and not result.needs_action and not isCritical:
                        priceData = await ltvManager.alchemyClient.get_asset_current_price(chainId=ltvManager.chainId, assetAddress=position.collateralAsset)
                        collateralValue = (position.collateralAmount / 1e18) * priceData.priceUsd
                        debtValue = position.borrowAmount / 1e6
                        await notificationService.send_daily_digest(
                            agent=agent,
                            user=user,
                            currentLtv=currentLtv,
                            collateralValue=collateralValue,
                            debtValue=debtValue,
                        )

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
        await monitor_positions(ltvManager, notificationService, agentManager)
    finally:
        await agentManager.requester.close_connections()


if __name__ == '__main__':
    asyncio.run(main())
