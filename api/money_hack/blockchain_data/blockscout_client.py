import asyncio
import random
import typing

from core.caching.cache import Cache
from core.exceptions import KibaException
from core.exceptions import TooManyRequestsException
from core.requester import Requester
from core.util import chain_util
from core.util.typing_util import JsonObject
from pydantic import BaseModel
from pydantic import Field

from money_hack import constants


class BlockscoutLog(BaseModel):
    address: str | None = None
    blockNumber: str | None = None
    logIndex: str | None = None
    topics: list[str | None] = Field(default_factory=list)
    data: str | None = None
    transactionHash: str | None = None
    transactionIndex: str | None = None
    removed: bool = False


class BlockscoutClient:
    def __init__(self, requester: Requester, cache: Cache, apiKey: str = '') -> None:
        self.requester = requester
        self.cache = cache
        self.apiKey = apiKey

    def _get_old_api_base_url(self, chainId: int) -> str:
        if chainId == constants.BASE_CHAIN_ID:
            return 'https://base.blockscout.com/api'
        if chainId == constants.BASE_SEPOLIA_CHAIN_ID:
            return 'https://base-sepolia.blockscout.com/api'
        if chainId == constants.ETH_CHAIN_ID:
            return 'https://eth.blockscout.com/api'
        if chainId == constants.SCROLL_CHAIN_ID:
            return 'https://blockscout.scroll.io/api'
        raise KibaException(f'Unsupported chainId for Blockscout: {chainId}')

    async def _make_request(self, url: str, maxRetries: int = 5) -> JsonObject:
        baseDelay = 1.0
        attempt = 0
        while True:
            try:
                fullUrl = f'{url}{"&" if "?" in url else "?"}apikey={self.apiKey}' if self.apiKey else url
                response = await self.requester.get(url=fullUrl)
                responseJson = typing.cast(JsonObject, response.json())
            except TooManyRequestsException:
                if attempt >= maxRetries:
                    raise
                delay = baseDelay * (2**attempt) + random.uniform(0, 1)  # noqa: S311
                await asyncio.sleep(delay)
                attempt += 1
            else:
                return responseJson

    async def get_logs_by_topic(
        self,
        chainId: int,
        address: str,
        topic0: str,
        topic1: str | None = None,
        fromBlock: int | None = None,
        toBlock: int | None = None,
    ) -> list[BlockscoutLog]:
        oldApiBase = self._get_old_api_base_url(chainId=chainId)
        normalizedAddress = chain_util.normalize_address(address)
        fromBlockParam = fromBlock if fromBlock is not None else 0
        toBlockParam = toBlock if toBlock is not None else 'latest'
        url = f'{oldApiBase}?module=logs&action=getLogs&fromBlock={fromBlockParam}&toBlock={toBlockParam}&address={normalizedAddress}&topic0={topic0}'
        if topic1 is not None:
            url += f'&topic0_1_opr=and&topic1={topic1}'
        response = await self._make_request(url=url)
        result = response.get('result')
        if result is None:
            return []
        return [BlockscoutLog(**item) for item in result]  # type: ignore[arg-type]
