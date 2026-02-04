# ruff: noqa: T201
import asyncio
import os

import asyncclick as click
import devtools
from core import logging

import _path_fix  # type: ignore[import-not-found]  # noqa: F401
from money_hack.agent_manager import AgentManager
from money_hack.create_agent_manager import create_agent_manager

TELEGRAM_API_TOKEN = os.environ['TELEGRAM_API_TOKEN']


async def setup_webhook_if_needed(agentManager: AgentManager, webhookUrl: str) -> None:
    print(f'Setting up webhook for Telegram bot: {webhookUrl}')
    currentWebhookInfo = await agentManager.telegramClient.get_bot_webhook_info()
    devtools.debug(currentWebhookInfo)
    if currentWebhookInfo.url == webhookUrl:
        print(f'✅ Webhook already configured correctly: {webhookUrl}')
        return
    print(f'🔧 Setting up webhook: {webhookUrl}')
    try:
        await agentManager.telegramClient.set_bot_webhook(webhookUrl=webhookUrl)
    except Exception as e:  # noqa: BLE001
        print(f'❌ Failed to set webhook: {e}')
        return
    print(f'✅ Webhook set successfully!')


@click.command()
@click.option('--webhook-url', 'webhookUrl', required=True, help='Webhook URL endpoint')
async def main(webhookUrl: str) -> None:
    logging.basicConfig(level=logging.INFO)
    agentManager = create_agent_manager()
    await agentManager.databaseStore.database.connect()
    try:
        async with agentManager.databaseStore.database.create_context_connection():
            await setup_webhook_if_needed(agentManager=agentManager, webhookUrl=webhookUrl)
    finally:
        await agentManager.requester.close_connections()
        await agentManager.databaseStore.database.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
