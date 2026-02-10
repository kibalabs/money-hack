#!/usr/bin/env python3
"""Close an agent position using the AgentManager flow."""

import argparse
import asyncio

from core import logging

import _path_fix  # noqa: F401
from money_hack.create_agent_manager import create_agent_manager


logging.init_basic_logging()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Close an agent position')
    parser.add_argument('--user-address', required=True)
    parser.add_argument('--agent-id', required=True)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    agentManager = create_agent_manager()
    try:
        await agentManager.databaseStore.database.connect()
        async with agentManager.databaseStore.database.create_context_connection():
            closeData = await agentManager.execute_close_position(user_address=args.user_address, agent_id=args.agent_id)
            logging.info(f'Close position tx hash: {closeData.transaction_hash}')
            logging.info(f'Collateral: {closeData.collateral_amount} Repay: {closeData.repay_amount} Vault withdraw: {closeData.vault_withdraw_amount}')
    finally:
        await agentManager.requester.close_connections()
        await agentManager.databaseStore.database.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
