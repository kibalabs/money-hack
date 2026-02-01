import asyncio
import typing

from core import logging
from core.requester import Requester
from core.web3.eth_client import RestEthClient
from eth_typing import ABI
from eth_typing import ABIEvent
from pydantic import BaseModel
from web3 import Web3

from money_hack import constants
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.yo import yo_abis

VAULT_ADDRESS_MAP: dict[int, str] = {
    constants.BASE_CHAIN_ID: '0x0000000f2eB9f69274678c76222B35eEc7588a65',
}
FALLBACK_APY = 0.08


class YoVaultInfo(BaseModel):
    address: str
    name: str
    symbol: str
    asset_address: str
    decimals: int
    total_assets: int
    apy: float


class YoClient:
    def __init__(self, requester: Requester, ethClient: RestEthClient, blockscoutClient: BlockscoutClient) -> None:
        self.requester = requester
        self.ethClient = ethClient
        self.blockscoutClient = blockscoutClient

    def _get_event_topic(self, abi: ABI, eventName: str) -> str:
        eventAbi = typing.cast(ABIEvent | None, next((item for item in abi if item.get('type') == 'event' and item.get('name') == eventName), None))
        if eventAbi is None:
            raise ValueError(f'Event {eventName} not found in ABI')
        types = [inp['type'] for inp in eventAbi.get('inputs', [])]
        signature = f'{eventName}({",".join(types)})'
        return '0x' + Web3.keccak(text=signature).hex()

    async def _get_share_price_update_blocks(self, chainId: int, vaultAddress: str, numUpdates: int = 2) -> list[int]:
        oracleAddressResponse = await self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='ORACLE_ADDRESS', arguments={})
        oracleAddress = oracleAddressResponse[0]
        sharePriceUpdatedTopic = self._get_event_topic(abi=yo_abis.ORACLE_ABI, eventName='SharePriceUpdated')
        vaultAddressTopic = '0x' + vaultAddress[2:].lower().zfill(64)
        latestBlock = await self.ethClient.get_latest_block_number()
        maxLookbackBlocks = int((3 * 24 * constants.SECONDS_PER_HOUR) / constants.BASE_BLOCK_TIME_SECONDS)
        fromBlock = max(latestBlock - maxLookbackBlocks, 0)
        logs = await self.blockscoutClient.get_logs_by_topic(chainId=chainId, address=oracleAddress, topic0=sharePriceUpdatedTopic, topic1=vaultAddressTopic, fromBlock=fromBlock, toBlock=latestBlock)
        updateBlocks = sorted((int(str(log.blockNumber), 16) for log in logs), reverse=True)
        return updateBlocks[:numUpdates]

    async def _calculate_apy_from_share_price_updates(self, chainId: int, vaultAddress: str, decimals: int) -> float:
        minUpdates = 2
        updateBlocks = await self._get_share_price_update_blocks(chainId=chainId, vaultAddress=vaultAddress, numUpdates=minUpdates)
        if len(updateBlocks) < minUpdates:
            logging.info(f'Not enough share price updates for {vaultAddress}, returning fallback APY')
            return FALLBACK_APY
        block1 = int(updateBlocks[1])
        block2 = int(updateBlocks[0])
        rate1Response, rate2Response, blockData1, blockData2 = await asyncio.gather(
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='convertToAssets', arguments={'shares': 10**decimals}, blockNumber=block1),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='convertToAssets', arguments={'shares': 10**decimals}, blockNumber=block2),
            self.ethClient.get_block(blockNumber=block1),
            self.ethClient.get_block(blockNumber=block2),
        )
        rate1 = int(rate1Response[0])
        rate2 = int(rate2Response[0])
        timestamp1 = int(blockData1['timestamp'])
        timestamp2 = int(blockData2['timestamp'])
        if rate1 <= 0 or rate2 <= rate1:
            return FALLBACK_APY
        secondsElapsed = timestamp2 - timestamp1
        if secondsElapsed <= 0:
            return FALLBACK_APY
        rateChange = rate2 / rate1
        apy = float((rateChange) ** (constants.SECONDS_PER_YEAR / secondsElapsed)) - 1
        logging.info(f'Yo vault {vaultAddress}: Calculated APY from share price updates. Rate change: {rateChange:.6f}, Time: {secondsElapsed}s, APY: {apy:.4%}')
        return apy

    async def get_vault_info(self, chainId: int) -> YoVaultInfo | None:
        vaultAddress = VAULT_ADDRESS_MAP.get(chainId)
        if vaultAddress is None:
            return None
        nameResponse, symbolResponse, assetResponse, decimalsResponse, totalAssetsResponse = await asyncio.gather(
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='name'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='symbol'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='asset'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='decimals'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='totalAssets'),
        )
        decimals = int(decimalsResponse[0])
        apy = await self._calculate_apy_from_share_price_updates(chainId=chainId, vaultAddress=vaultAddress, decimals=decimals)
        logging.info(f'Yo vault info loaded: {nameResponse[0]}, TVL: {int(totalAssetsResponse[0]) / 10**6:.2f} USDC, APY: {apy:.2%}')
        return YoVaultInfo(
            address=vaultAddress,
            name=str(nameResponse[0]),
            symbol=str(symbolResponse[0]),
            asset_address=str(assetResponse[0]),
            decimals=decimals,
            total_assets=int(totalAssetsResponse[0]),
            apy=apy,
        )

    async def get_yield_apy(self, chainId: int) -> float | None:
        vaultAddress = VAULT_ADDRESS_MAP.get(chainId)
        if vaultAddress is None:
            return None
        decimalsResponse = await self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=yo_abis.VAULT_ABI, functionName='decimals')
        decimals = int(decimalsResponse[0])
        return await self._calculate_apy_from_share_price_updates(chainId=chainId, vaultAddress=vaultAddress, decimals=decimals)
