#!/usr/bin/env python3
"""
One-off script to fix vault shares in existing agent positions.
This updates positions that have USDC amounts stored in vaultShares
to the actual on-chain vault share values.
"""

import asyncio
import os
from urllib.parse import quote_plus

import sqlalchemy
from core import logging
from core.requester import Requester
from core.store.database import Database
from core.web3.eth_client import RestEthClient

# Import path fix
import _path_fix  # noqa: F401
from money_hack.morpho import morpho_abis

logging.init_basic_logging()

YO_VAULT_ADDRESS = '0x0000000f2eB9f69274678c76222B35eEc7588a65'


async def get_actual_vault_balance(ethClient: RestEthClient, agentWalletAddress: str) -> tuple[int, int]:
    """Get actual vault shares and their USDC value from on-chain data.
    Returns: (shares, assets_in_usdc)
    """
    sharesResponse = await ethClient.call_function_by_name(
        toAddress=YO_VAULT_ADDRESS,
        contractAbi=morpho_abis.ERC4626_VAULT_ABI,
        functionName='balanceOf',
        arguments={'account': agentWalletAddress},
    )
    shares = int(sharesResponse[0])
    if shares == 0:
        return 0, 0
    assetsResponse = await ethClient.call_function_by_name(
        toAddress=YO_VAULT_ADDRESS,
        contractAbi=morpho_abis.ERC4626_VAULT_ABI,
        functionName='convertToAssets',
        arguments={'shares': shares},
    )
    assets = int(assetsResponse[0])
    return shares, assets


async def main() -> None:
    # Set up database and eth client
    BASE_CHAIN_ID = 8453
    BASE_RPC_URL = os.environ['BASE_RPC_URL']
    DB_HOST = os.environ['DB_HOST']
    DB_PORT = os.environ['DB_PORT']
    DB_NAME = os.environ['DB_NAME']
    DB_USERNAME = os.environ['DB_USERNAME']
    DB_PASSWORD = os.environ['DB_PASSWORD']

    requester = Requester()
    ethClient = RestEthClient(url=BASE_RPC_URL, chainId=BASE_CHAIN_ID, requester=requester)
    encodedPassword = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    databaseConnectionString = f'postgresql+asyncpg://{DB_USERNAME}:{encodedPassword}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    database = Database(connectionString=databaseConnectionString)

    try:
        # Connect to database
        await database.connect()
        logging.info('Connected to database')

        async with database.create_context_connection():
            # Get all positions with non-zero vault shares
            query = """
                SELECT
                    ap.id as position_id,
                    ap.agent_id,
                    ap.vault_shares,
                    a.wallet_address
                FROM tbl_agent_positions ap
                JOIN tbl_agents a ON ap.agent_id = a.id
                WHERE ap.vault_shares > 0
                ORDER BY ap.id
            """
            result = await database.execute(query=sqlalchemy.text(query))  # type: ignore[arg-type]
            rows = result.fetchall()
            logging.info(f'Found {len(rows)} positions with vault shares')

            updatedCount = 0
            skippedCount = 0

            for row in rows:
                positionId = row[0]  # position_id
                agentId = row[1]  # agent_id
                dbVaultShares = int(row[2])  # vault_shares
                walletAddress = row[3]  # wallet_address

                logging.info(f'\nProcessing position {positionId} for agent {agentId}')
                logging.info(f'  Wallet: {walletAddress}')
                logging.info(f'  DB vault shares: {dbVaultShares}')

                # Get actual vault balance from blockchain
                actualShares, actualAssets = await get_actual_vault_balance(ethClient, walletAddress)
                logging.info(f'  Actual vault shares: {actualShares}')
                logging.info(f'  Actual vault assets (USDC): {actualAssets}')

                # Check if we need to update
                if actualShares == dbVaultShares:
                    logging.info(f'  ✓ Shares already correct, skipping')
                    skippedCount += 1
                    continue

                # Update the database
                updateQuery = sqlalchemy.text("""
                    UPDATE tbl_agent_positions
                    SET vault_shares = :vault_shares, updated_date = NOW()
                    WHERE id = :position_id
                """)
                updateQuery = updateQuery.bindparams(
                    vault_shares=actualShares,
                    position_id=positionId,
                )
                await database.execute(query=updateQuery)  # type: ignore[arg-type]
                logging.info(f'  ✓ Updated vault shares from {dbVaultShares} to {actualShares}')
                updatedCount += 1

            logging.info(f'\n=== Summary ===')
            logging.info(f'Total positions: {len(rows)}')
            logging.info(f'Updated: {updatedCount}')
            logging.info(f'Skipped (already correct): {skippedCount}')

    finally:
        # Clean up
        await requester.close_connections()
        await database.disconnect()
        logging.info('Cleanup complete')


if __name__ == '__main__':
    asyncio.run(main())
