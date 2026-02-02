import asyncio

from core import logging
from core.requester import Requester
from core.web3.eth_client import RestEthClient
from pydantic import BaseModel

from money_hack import constants
from money_hack.blockchain_data.blockscout_client import BlockscoutClient
from money_hack.forty_acres import forty_acres_abis

VAULT_ADDRESS_MAP: dict[int, str] = {
    constants.BASE_CHAIN_ID: '0xB99B6dF96d4d5448cC0a5B3e0ef7896df9507Cf5',
}


class FortyAcresVaultInfo(BaseModel):
    address: str
    name: str
    symbol: str
    asset_address: str
    decimals: int
    total_assets: int
    apy: float


class FortyAcresClient:
    def __init__(self, requester: Requester, ethClient: RestEthClient, blockscoutClient: BlockscoutClient) -> None:
        self.requester = requester
        self.ethClient = ethClient
        self.blockscoutClient = blockscoutClient

    async def _calculate_apy_from_share_price_updates(self, _chainId: int, vaultAddress: str, decimals: int) -> float:
        latestBlock = await self.ethClient.get_latest_block_number()
        maxLookbackBlocks = int((7 * 24 * constants.SECONDS_PER_HOUR) / constants.BASE_BLOCK_TIME_SECONDS)
        fromBlock = max(latestBlock - maxLookbackBlocks, 0)
        rate1Response = await self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='convertToAssets', arguments={'shares': 10**decimals}, blockNumber=fromBlock)
        rate2Response = await self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='convertToAssets', arguments={'shares': 10**decimals}, blockNumber=latestBlock)
        blockData1, blockData2 = await asyncio.gather(
            self.ethClient.get_block(blockNumber=fromBlock),
            self.ethClient.get_block(blockNumber=latestBlock),
        )
        rate1 = int(rate1Response[0])
        rate2 = int(rate2Response[0])
        timestamp1 = int(blockData1['timestamp'])
        timestamp2 = int(blockData2['timestamp'])
        if rate1 <= 0 or rate2 <= rate1:
            raise ValueError(f'Invalid share price data for {vaultAddress}: rate1={rate1}, rate2={rate2}')
        secondsElapsed = timestamp2 - timestamp1
        if secondsElapsed <= 0:
            raise ValueError(f'Invalid timestamps for {vaultAddress}: t1={timestamp1}, t2={timestamp2}')
        rateChange = rate2 / rate1
        apy = float((rateChange) ** (constants.SECONDS_PER_YEAR / secondsElapsed)) - 1
        logging.info(f'40acres vault {vaultAddress}: Calculated APY from share price updates. Rate change: {rateChange:.6f}, Time: {secondsElapsed}s, APY: {apy:.4%}')
        return apy

    async def get_vault_info(self, chainId: int) -> FortyAcresVaultInfo | None:
        vaultAddress = VAULT_ADDRESS_MAP.get(chainId)
        if vaultAddress is None:
            return None
        nameResponse, symbolResponse, assetResponse, decimalsResponse, totalAssetsResponse = await asyncio.gather(
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='name'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='symbol'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='asset'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='decimals'),
            self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='totalAssets'),
        )
        decimals = int(decimalsResponse[0])
        apy = await self._calculate_apy_from_share_price_updates(_chainId=chainId, vaultAddress=vaultAddress, decimals=decimals)
        logging.info(f'40acres vault info loaded: {nameResponse[0]}, TVL: {int(totalAssetsResponse[0]) / 10**6:.2f} USDC, APY: {apy:.2%}')
        return FortyAcresVaultInfo(
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
        decimalsResponse = await self.ethClient.call_function_by_name(toAddress=vaultAddress, contractAbi=forty_acres_abis.VAULT_ABI, functionName='decimals')
        decimals = int(decimalsResponse[0])
        return await self._calculate_apy_from_share_price_updates(_chainId=chainId, vaultAddress=vaultAddress, decimals=decimals)
