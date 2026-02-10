#!/usr/bin/env python3
"""
Diagnostic script to pull all on-chain data for an agent's position.
Shows wallet balances, Morpho position, vault balance, and overall state.
"""

import asyncio
import os
from urllib.parse import quote_plus

import sqlalchemy
from core import logging
from core.requester import Requester
from core.web3.eth_client import RestEthClient

import _path_fix  # noqa: F401
from money_hack.morpho import morpho_abis

logging.init_basic_logging()

MORPHO_BLUE_ADDRESS = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb'
YO_VAULT_ADDRESS = '0x0000000f2eB9f69274678c76222B35eEc7588a65'
USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
CBBTC_ADDRESS = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
WETH_ADDRESS = '0x4200000000000000000000000000000000000006'

ERC20_BALANCE_OF_ABI: list[dict[str, object]] = [
    {
        'inputs': [{'name': 'account', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]


async def main() -> None:
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

    from core.store.database import Database

    database = Database(connectionString=databaseConnectionString)

    try:
        await database.connect()
        logging.info('Connected to database')

        async with database.create_context_connection():
            # Get all active positions with agent wallet addresses
            query = """
                SELECT
                    ap.id as position_id,
                    ap.agent_id,
                    ap.collateral_asset,
                    ap.target_ltv,
                    ap.morpho_market_id,
                    ap.status,
                    a.wallet_address,
                    a.name as agent_name
                FROM tbl_agent_positions ap
                JOIN tbl_agents a ON ap.agent_id = a.id
                WHERE ap.status = 'active'
                ORDER BY ap.id
            """
            result: sqlalchemy.engine.Result = await database.execute(query=sqlalchemy.text(query))  # type: ignore[arg-type,assignment]
            rows = result.fetchall()
            logging.info(f'Found {len(rows)} active positions')

            for row in rows:
                positionId = row[0]
                agentId = row[1]
                collateralAsset = row[2]
                targetLtv = row[3]
                morphoMarketId = row[4]
                status = row[5]
                walletAddress = row[6]
                agentName = row[7]

                collateralSymbol = 'cbBTC' if collateralAsset.lower() == CBBTC_ADDRESS.lower() else 'WETH'
                collateralDecimals = 8 if collateralSymbol == 'cbBTC' else 18

                print(f'\n{"=" * 80}')
                print(f'Agent: {agentName} (ID: {agentId})')
                print(f'Wallet: {walletAddress}')
                print(f'Position ID: {positionId} | Status: {status}')
                print(f'Collateral: {collateralSymbol} ({collateralAsset})')
                print(f'Target LTV: {targetLtv:.2%}')
                print(f'Morpho Market ID: {morphoMarketId}')
                print(f'{"=" * 80}')

                # 1. Wallet balances (ERC20 balanceOf)
                print('\n--- WALLET BALANCES ---')

                # cbBTC balance
                cbbtcResponse = await ethClient.call_function_by_name(
                    toAddress=CBBTC_ADDRESS,
                    contractAbi=ERC20_BALANCE_OF_ABI,
                    functionName='balanceOf',
                    arguments={'account': walletAddress},
                )
                cbbtcBalance = int(cbbtcResponse[0])
                print(f'  cbBTC:  {cbbtcBalance} raw = {cbbtcBalance / 1e8:.8f} cbBTC')

                # WETH balance
                wethResponse = await ethClient.call_function_by_name(
                    toAddress=WETH_ADDRESS,
                    contractAbi=ERC20_BALANCE_OF_ABI,
                    functionName='balanceOf',
                    arguments={'account': walletAddress},
                )
                wethBalance = int(wethResponse[0])
                print(f'  WETH:   {wethBalance} raw = {wethBalance / 1e18:.8f} WETH')

                # USDC balance
                usdcResponse = await ethClient.call_function_by_name(
                    toAddress=USDC_ADDRESS,
                    contractAbi=ERC20_BALANCE_OF_ABI,
                    functionName='balanceOf',
                    arguments={'account': walletAddress},
                )
                usdcBalance = int(usdcResponse[0])
                print(f'  USDC:   {usdcBalance} raw = ${usdcBalance / 1e6:.6f}')

                # 2. Morpho Blue position
                print('\n--- MORPHO BLUE POSITION ---')
                marketIdBytes = bytes.fromhex(morphoMarketId[2:]) if morphoMarketId.startswith('0x') else bytes.fromhex(morphoMarketId)

                positionResponse = await ethClient.call_function_by_name(
                    toAddress=MORPHO_BLUE_ADDRESS,
                    contractAbi=morpho_abis.MORPHO_BLUE_ABI,
                    functionName='position',
                    arguments={'id': marketIdBytes, 'user': walletAddress},
                )
                supplyShares = int(positionResponse[0])
                borrowShares = int(positionResponse[1])
                collateralAmount = int(positionResponse[2])
                print(f'  Supply Shares:  {supplyShares}')
                print(f'  Borrow Shares:  {borrowShares}')
                print(f'  Collateral:     {collateralAmount} raw = {collateralAmount / (10**collateralDecimals):.8f} {collateralSymbol}')

                # Get market state to convert borrow shares to assets
                marketResponse = await ethClient.call_function_by_name(
                    toAddress=MORPHO_BLUE_ADDRESS,
                    contractAbi=morpho_abis.MORPHO_BLUE_ABI,
                    functionName='market',
                    arguments={'id': marketIdBytes},
                )
                totalSupplyAssets = int(marketResponse[0])
                totalSupplyShares = int(marketResponse[1])
                totalBorrowAssets = int(marketResponse[2])
                totalBorrowShares = int(marketResponse[3])
                print(f'  Market totalBorrowAssets:  {totalBorrowAssets} = ${totalBorrowAssets / 1e6:.2f}')
                print(f'  Market totalBorrowShares:  {totalBorrowShares}')

                borrowAmount = 0
                if borrowShares > 0 and totalBorrowShares > 0:
                    borrowAmount = (borrowShares * totalBorrowAssets + totalBorrowShares - 1) // totalBorrowShares
                print(f'  Borrow Amount:  {borrowAmount} raw = ${borrowAmount / 1e6:.6f} USDC')

                # 3. Yo Vault balance
                print('\n--- YO VAULT BALANCE ---')
                sharesResponse = await ethClient.call_function_by_name(
                    toAddress=YO_VAULT_ADDRESS,
                    contractAbi=morpho_abis.ERC4626_VAULT_ABI,
                    functionName='balanceOf',
                    arguments={'account': walletAddress},
                )
                vaultShares = int(sharesResponse[0])
                vaultAssets = 0
                if vaultShares > 0:
                    assetsResponse = await ethClient.call_function_by_name(
                        toAddress=YO_VAULT_ADDRESS,
                        contractAbi=morpho_abis.ERC4626_VAULT_ABI,
                        functionName='convertToAssets',
                        arguments={'shares': vaultShares},
                    )
                    vaultAssets = int(assetsResponse[0])
                print(f'  Vault Shares:   {vaultShares}')
                print(f'  Vault Assets:   {vaultAssets} raw = ${vaultAssets / 1e6:.6f} USDC')

                # 4. Overall summary
                print('\n--- OVERALL AGENT STATE ---')
                print(f'  Wallet {collateralSymbol}:      {collateralAmount / (10**collateralDecimals):.8f} (in Morpho as collateral)')
                print(f'  Wallet {collateralSymbol} free:  {cbbtcBalance / 1e8:.8f} (in wallet, not deposited)')
                print(f'  USDC borrowed:       ${borrowAmount / 1e6:.6f}')
                print(f'  USDC in vault:       ${vaultAssets / 1e6:.6f}')
                print(f'  USDC in wallet:      ${usdcBalance / 1e6:.6f}')
                if collateralAmount > 0:
                    # We can't get price here easily, but we can compute LTV from the data we have
                    print('  Current LTV:         needs price to calculate')
                else:
                    print('  Current LTV:         N/A (no collateral in Morpho)')
                print(f'  Target LTV:          {targetLtv:.2%}')

    finally:
        await requester.close_connections()
        await database.disconnect()
        logging.info('Cleanup complete')


if __name__ == '__main__':
    asyncio.run(main())
