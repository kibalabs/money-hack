import asyncio
import datetime
import random

from core import logging
from core.caching.cache import Cache
from core.exceptions import InternalServerErrorException
from core.exceptions import TooManyRequestsException
from core.requester import Requester
from core.util import date_util

from money_hack import util

# Cache historical block lookups for 1 year since they never change
CACHE_EXPIRY_SECONDS = 60 * 60 * 24 * 365


class FindBlockClient:
    def __init__(self, requester: Requester, cache: Cache | None = None) -> None:
        self.requester = requester
        self.cache = cache

    async def get_block_number_at_timestamp(self, chainId: int, timestamp: int) -> int:
        cacheKey = f'findblock-block-number-{chainId}-{timestamp}'
        cachedBlockNumber = await util.get_json_from_optional_cache(cache=self.cache, key=cacheKey)
        if cachedBlockNumber is not None:
            return int(cachedBlockNumber)
        maxRetries = 5
        baseDelay = 1.0
        attempt = 0
        while True:
            try:
                response = await self.requester.get(url=f'https://api.findblock.xyz/v1/chain/{chainId}/block/before/{timestamp}', dataDict={'inclusive': True}, timeout=60)
                responseData = response.json()
                if 'number' not in responseData:
                    raise InternalServerErrorException(f'Invalid response from FindBlock API: {responseData}')
                blockNumber = int(responseData['number'])
                await util.save_json_to_optional_cache(cache=self.cache, key=cacheKey, value=blockNumber, expirySeconds=CACHE_EXPIRY_SECONDS)
            except TooManyRequestsException:
                if attempt >= maxRetries:
                    raise
                logging.info(f'Too many requests to FindBlock API, retrying in {baseDelay * (2**attempt):.1f} seconds...')
                delay = baseDelay * (2**attempt) + random.uniform(0, 1)  # noqa: S311
                await asyncio.sleep(delay)
                attempt += 1
            else:
                return blockNumber

    async def get_block_number_at_date_start(self, chainId: int, date: datetime.date) -> int:
        timestamp = date_util.start_of_day(dt=date_util.datetime_from_date(date=date))
        timestampUnix = int(timestamp.timestamp())
        return await self.get_block_number_at_timestamp(chainId=chainId, timestamp=timestampUnix)
