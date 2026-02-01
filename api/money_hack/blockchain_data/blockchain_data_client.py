import datetime
from abc import ABC
from abc import abstractmethod

from core.caching.cache import Cache
from core.exceptions import NotFoundException
from core.util import date_util
from pydantic import BaseModel


class PriceNotFoundException(NotFoundException):
    pass


class ClientAsset(BaseModel):
    address: str
    decimals: int
    name: str
    symbol: str
    logoUri: str | None
    totalSupply: int
    isSpam: bool


class ClientAssetPrice(BaseModel):
    priceUsd: float


class ClientAssetBalance(BaseModel):
    assetAddress: str
    balance: int


class ClientWalletErc20Transfer(BaseModel):
    blockNumber: int
    transactionHash: str
    fromAddress: str
    toAddress: str
    assetAddress: str
    assetAmount: int
    logIndex: int | None = None


class BlockchainDataClient(ABC):
    def __init__(self, cache: Cache | None = None) -> None:
        self.cache = cache

    async def get_block_number_at_date_end(self, chainId: int, date: datetime.date) -> int:
        return await self.get_block_number_at_date_start(chainId=chainId, date=date_util.date_from_date(date=date, days=1))

    @abstractmethod
    async def get_block_number_at_date_start(self, chainId: int, date: datetime.date) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_asset(self, chainId: int, assetAddress: str) -> ClientAsset:
        raise NotImplementedError

    @abstractmethod
    async def get_asset_current_price(self, chainId: int, assetAddress: str) -> ClientAssetPrice:
        raise NotImplementedError

    @abstractmethod
    async def get_asset_price_at_block(self, chainId: int, assetAddress: str, blockNumber: int) -> ClientAssetPrice:
        raise NotImplementedError

    @abstractmethod
    async def get_asset_historic_price(self, chainId: int, assetAddress: str, date: datetime.date) -> ClientAssetPrice:
        raise NotImplementedError

    @abstractmethod
    async def get_wallet_asset_balances(self, chainId: int, walletAddress: str) -> list[ClientAssetBalance]:
        raise NotImplementedError

    @abstractmethod
    async def list_wallet_erc20_transfers(self, chainId: int, walletAddress: str, fromBlock: int, toBlock: int) -> list[ClientWalletErc20Transfer]:
        raise NotImplementedError
