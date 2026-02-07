#!/usr/bin/env python3
"""
Script to register an ENS subname and set constitution text records on mainnet.

Usage:
    source .envrc && python scripts/set_ens_constitution.py

This will:
1. Look up the first agent from the database
2. If no ENS name, register a subname under borrowbott.eth (via deployer, 1 tx)
3. Set constitution + status text records in a SINGLE multicall transaction
4. Read them back to verify
"""

import asyncio
import os
import re
from urllib.parse import quote_plus

import sqlalchemy
from core import logging
from core.requester import Requester
from core.store.database import Database
from core.web3.eth_client import RestEthClient
from web3 import Web3
from web3.types import TxParams

import _path_fix  # noqa: F401
from money_hack.external.ens_client import EnsClient
from money_hack.external.ens_client import EnsConstitution

logging.init_basic_logging()

MAINNET_CHAIN_ID = 1


async def send_deployer_transaction(ethClient: RestEthClient, deployerPrivateKey: str, txParams: TxParams) -> str:
    """Send a transaction signed by the deployer wallet on mainnet."""
    deployerAddress = Web3().eth.account.from_key(deployerPrivateKey).address
    txParams['from'] = deployerAddress  # type: ignore[typeddict-item]
    filledParams = await ethClient.fill_transaction_params(params=txParams, fromAddress=deployerAddress)
    signed = Web3().eth.account.sign_transaction(transaction_dict=filledParams, private_key=deployerPrivateKey)
    txHash = await ethClient.send_raw_transaction(transactionData=signed.raw_transaction.hex())
    logging.info(f'Deployer transaction sent: {txHash}')
    await ethClient.wait_for_transaction_receipt(transactionHash=txHash)
    logging.info(f'Deployer transaction confirmed: {txHash}')
    return txHash


async def main() -> None:
    # Environment
    ALCHEMY_API_KEY = os.environ['ALCHEMY_API_KEY']
    MAINNET_RPC_URL = os.environ.get('MAINNET_RPC_URL', f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}')
    DEPLOYER_PRIVATE_KEY = os.environ['DEPLOYER_PRIVATE_KEY']
    DB_HOST = os.environ['DB_HOST']
    DB_PORT = os.environ['DB_PORT']
    DB_NAME = os.environ['DB_NAME']
    DB_USERNAME = os.environ['DB_USERNAME']
    DB_PASSWORD = os.environ['DB_PASSWORD']

    # Clients
    requester = Requester()
    ethClient = RestEthClient(url=MAINNET_RPC_URL, chainId=MAINNET_CHAIN_ID, requester=requester)
    ensClient = EnsClient(requester=requester, chainId=MAINNET_CHAIN_ID)

    deployerAddress = Web3().eth.account.from_key(DEPLOYER_PRIVATE_KEY).address
    print(f'Deployer address: {deployerAddress}')

    # Database
    encodedPassword = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    databaseConnectionString = f'postgresql+asyncpg://{DB_USERNAME}:{encodedPassword}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    database = Database(connectionString=databaseConnectionString)

    try:
        await database.connect()
        logging.info('Connected to database')

        async with database.create_context_connection():
            # Find agent
            query = """
                SELECT a.id, a.name, a.emoji, a.wallet_address, a.ens_name
                FROM tbl_agents a
                ORDER BY a.created_date DESC
                LIMIT 1
            """
            result: sqlalchemy.engine.Result = await database.execute(query=sqlalchemy.text(query))  # type: ignore[arg-type,assignment]
            row = result.fetchone()
            if not row:
                print('No agents found in database')
                return

            agentId = str(row[0])
            agentName = row[1]
            agentEmoji = row[2]
            walletAddress = row[3]
            ensName = row[4]

            print(f'\n{"=" * 60}')
            print(f'Agent: {agentEmoji} {agentName}')
            print(f'Agent ID: {agentId}')
            print(f'Wallet: {walletAddress}')
            print(f'ENS Name: {ensName or "(none)"}')
            print(f'{"=" * 60}')

            # Step 1: Register subname on mainnet via NameWrapper if needed
            if not ensName:
                print('\n--- Registering ENS subname via NameWrapper on mainnet ---')
                ensLabel = re.sub(r'[^a-z0-9-]', '', agentName.lower().replace(' ', '-'))
                if len(ensLabel) < 3:
                    ensLabel = 'agent-0'
                ensName = ensClient.get_full_ens_name(ensLabel)
                print(f'  Label: {ensLabel}')
                print(f'  Full name: {ensName}')
                print(f'  Owner: {walletAddress}')

                from money_hack.external.ens_client import namehash, ENS_NAME_WRAPPER_ADDRESS, ENS_NAME_WRAPPER_ABI, PARENT_NAME

                # Get parent name expiry from NameWrapper (needed for subname expiry)
                parentNode = namehash(PARENT_NAME)
                parentTokenId = int.from_bytes(parentNode, 'big')
                parentData = await ethClient.call_function_by_name(
                    toAddress=ENS_NAME_WRAPPER_ADDRESS,
                    contractAbi=ENS_NAME_WRAPPER_ABI,
                    functionName='getData',
                    arguments={'id': parentTokenId},
                )
                parentOwner = parentData[0]
                parentExpiry = parentData[2]
                print(f'  Parent NameWrapper owner: {parentOwner}')
                print(f'  Parent expiry: {parentExpiry}')

                if parentOwner == '0x0000000000000000000000000000000000000000':
                    print('  ERROR: borrowbott.eth is NOT wrapped in NameWrapper!')
                    print('  Please wrap it first via the ENS Manager App.')
                    return

                # Check if subname is already wrapped in NameWrapper
                subnameNode = namehash(ensName)
                subnameTokenId = int.from_bytes(subnameNode, 'big')
                subnameData = await ethClient.call_function_by_name(
                    toAddress=ENS_NAME_WRAPPER_ADDRESS,
                    contractAbi=ENS_NAME_WRAPPER_ABI,
                    functionName='getData',
                    arguments={'id': subnameTokenId},
                )
                subnameOwner = subnameData[0]
                if subnameOwner and subnameOwner != '0x0000000000000000000000000000000000000000':
                    print(f'  Already wrapped in NameWrapper (owner: {subnameOwner}), skipping tx')
                else:
                    # Register via NameWrapper with DEPLOYER as owner
                    # (deployer needs to be the NameWrapper token owner to call setText on resolver)
                    subnameTx = ensClient.build_register_subname_transaction(
                        label=ensLabel, ownerAddress=deployerAddress, expiry=parentExpiry,
                    )
                    txParams: TxParams = {
                        'to': Web3.to_checksum_address(subnameTx.to),
                        'data': subnameTx.data,
                    }
                    txHash = await send_deployer_transaction(ethClient, DEPLOYER_PRIVATE_KEY, txParams)
                    print(f'  Registered via NameWrapper! TX: {txHash}')
                    print(f'  View: https://etherscan.io/tx/{txHash}')

                # Update DB
                updateQuery = sqlalchemy.text("UPDATE tbl_agents SET ens_name = :ens_name WHERE id = CAST(:agent_id AS uuid)").bindparams(ens_name=ensName, agent_id=agentId)
                await database.execute(query=updateQuery)  # type: ignore[arg-type]
                print(f'  Updated database with ens_name={ensName}')

            # Step 2: Read current constitution
            print(f'\n--- Reading current constitution from {ensName} ---')
            constitution = await ensClient.read_constitution(ethClient, ensName)
            print(f'  max_ltv: {constitution.max_ltv}')
            print(f'  min_spread: {constitution.min_spread}')
            print(f'  max_position_usd: {constitution.max_position_usd}')
            print(f'  allowed_collateral: {constitution.allowed_collateral}')
            print(f'  pause: {constitution.pause}')

            status = await ensClient.read_status(ethClient, ensName)
            print(f'\n--- Current status ---')
            print(f'  status: {status.status}')
            print(f'  last_action: {status.last_action}')
            print(f'  last_check: {status.last_check}')

            # Step 3: Set constitution + status in a SINGLE multicall transaction
            print('\n--- Building multicall transaction (all records in 1 tx) ---')
            constitution_to_set = EnsConstitution(
                max_ltv=0.80,
                min_spread=0.005,
                max_position_usd=50000,
                allowed_collateral='cbBTC,WETH',
                pause=False,
            )
            multicallTx = ensClient.build_full_constitution_multicall(
                ensName=ensName,
                constitution=constitution_to_set,
                status='active',
                lastAction='constitution initialized',
                lastCheck='pending',
            )
            print(f'  Multicall target: {multicallTx.to}')
            print(f'  Records: 5 constitution + 3 status = 8 setText calls in 1 transaction')

            # Step 4: Submit single transaction via deployer
            print('\n--- Submitting multicall transaction on mainnet ---')
            txParams = {
                'to': Web3.to_checksum_address(multicallTx.to),
                'data': multicallTx.data,
            }
            txHash = await send_deployer_transaction(ethClient, DEPLOYER_PRIVATE_KEY, txParams)
            print(f'  Transaction hash: {txHash}')
            print(f'  View on Etherscan: https://etherscan.io/tx/{txHash}')

            # Step 5: Read back to verify
            print('\n--- Verifying: reading back constitution ---')
            await asyncio.sleep(5)
            constitution = await ensClient.read_constitution(ethClient, ensName)
            print(f'  max_ltv: {constitution.max_ltv}')
            print(f'  min_spread: {constitution.min_spread}')
            print(f'  max_position_usd: {constitution.max_position_usd}')
            print(f'  allowed_collateral: {constitution.allowed_collateral}')
            print(f'  pause: {constitution.pause}')

            status = await ensClient.read_status(ethClient, ensName)
            print(f'  status: {status.status}')
            print(f'  last_action: {status.last_action}')
            print(f'  last_check: {status.last_check}')

            print('\n--- Done! ---')
            print(f'View records at: https://app.ens.domains/{ensName}')
            print(f'Or via API: https://enstate.rs/n/{ensName}')

    finally:
        await requester.close_connections()
        await database.disconnect()
        logging.info('Cleanup complete')


if __name__ == '__main__':
    asyncio.run(main())
