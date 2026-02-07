import math
import time
from dataclasses import dataclass

from core import logging
from core.requester import Requester

from money_hack.blockchain_data.alchemy_client import AlchemyClient


@dataclass
class PriceAnalysis:
    asset_address: str
    current_price_usd: float
    change_1h_pct: float
    change_24h_pct: float
    change_7d_pct: float
    volatility_24h: float  # standard deviation of hourly returns over 24h
    trend: str  # 'up', 'down', 'sideways'

    def is_volatile(self, threshold: float = 0.02) -> bool:
        """Check if recent price action exceeds volatility threshold."""
        return abs(self.change_1h_pct) > threshold or self.volatility_24h > threshold

    def to_summary(self) -> str:
        direction = '+' if self.change_1h_pct >= 0 else ''
        return (
            f'Price: ${self.current_price_usd:,.2f} | '
            f'1h: {direction}{self.change_1h_pct:.2%} | '
            f'24h: {"+" if self.change_24h_pct >= 0 else ""}{self.change_24h_pct:.2%} | '
            f'7d: {"+" if self.change_7d_pct >= 0 else ""}{self.change_7d_pct:.2%} | '
            f'Vol(24h): {self.volatility_24h:.2%} | Trend: {self.trend}'
        )


@dataclass
class _CacheEntry:
    analysis: PriceAnalysis
    timestamp: float


CACHE_TTL_SECONDS = 900  # 15 minutes


class PriceIntelligenceService:
    """Provides historical price analysis using Alchemy's price APIs."""

    def __init__(self, alchemyClient: AlchemyClient, requester: Requester) -> None:
        self.alchemyClient = alchemyClient
        self.requester = requester
        self._cache: dict[str, _CacheEntry] = {}

    def _get_cached(self, key: str) -> PriceAnalysis | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry.timestamp > CACHE_TTL_SECONDS:
            del self._cache[key]
            return None
        return entry.analysis

    def _set_cached(self, key: str, analysis: PriceAnalysis) -> None:
        self._cache[key] = _CacheEntry(analysis=analysis, timestamp=time.time())

    async def _fetch_historical_prices(self, chainId: int, assetAddress: str, hours: int, interval: str = '1h') -> list[float]:
        """Fetch historical prices from Alchemy for the given time window."""
        import datetime

        from core.util import date_util

        now = datetime.datetime.now(tz=datetime.UTC)
        startTime = now - datetime.timedelta(hours=hours)
        networkName = self.alchemyClient._get_network_name(chainId=chainId)
        try:
            responseData = await self.alchemyClient._make_prices_api_request(
                path='tokens/historical',
                dataDict={
                    'startTime': date_util.datetime_to_string(dt=startTime, dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                    'endTime': date_util.datetime_to_string(dt=now, dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                    'interval': interval,
                    'network': networkName,
                    'address': assetAddress,
                },
            )
            if not responseData.get('data'):
                return []
            return [float(point['value']) for point in responseData['data'] if point.get('value')]
        except Exception as e:  # noqa: BLE001
            logging.warning(f'Failed to fetch historical prices for {assetAddress}: {e}')
            return []

    @staticmethod
    def _calculate_volatility(prices: list[float]) -> float:
        """Calculate the standard deviation of hourly returns."""
        if len(prices) < 2:
            return 0.0
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] > 0]
        if not returns:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance)

    @staticmethod
    def _determine_trend(change_24h: float, change_7d: float) -> str:
        """Determine price trend from recent changes."""
        if change_24h > 0.01 and change_7d > 0.02:
            return 'up'
        if change_24h < -0.01 and change_7d < -0.02:
            return 'down'
        return 'sideways'

    async def get_price_analysis(self, chainId: int, assetAddress: str) -> PriceAnalysis:
        """Get comprehensive price analysis for an asset. Cached for 15 minutes."""
        cacheKey = f'{chainId}-{assetAddress.lower()}'
        cached = self._get_cached(cacheKey)
        if cached is not None:
            return cached

        # Fetch current price
        currentPriceData = await self.alchemyClient.get_asset_current_price(chainId=chainId, assetAddress=assetAddress)
        currentPrice = currentPriceData.priceUsd

        # Fetch 24h hourly prices for volatility and short-term changes
        hourlyPrices = await self._fetch_historical_prices(chainId=chainId, assetAddress=assetAddress, hours=24, interval='1h')

        # Fetch 7d daily prices for longer-term trend
        dailyPrices = await self._fetch_historical_prices(chainId=chainId, assetAddress=assetAddress, hours=168, interval='1d')

        # Calculate changes
        change1h = 0.0
        change24h = 0.0
        change7d = 0.0

        if len(hourlyPrices) >= 2:
            change1h = (currentPrice - hourlyPrices[-1]) / hourlyPrices[-1] if hourlyPrices[-1] > 0 else 0.0
        if hourlyPrices:
            change24h = (currentPrice - hourlyPrices[0]) / hourlyPrices[0] if hourlyPrices[0] > 0 else 0.0
        if dailyPrices:
            change7d = (currentPrice - dailyPrices[0]) / dailyPrices[0] if dailyPrices[0] > 0 else 0.0

        volatility24h = self._calculate_volatility(hourlyPrices) if hourlyPrices else 0.0
        trend = self._determine_trend(change_24h=change24h, change_7d=change7d)

        analysis = PriceAnalysis(
            asset_address=assetAddress,
            current_price_usd=currentPrice,
            change_1h_pct=change1h,
            change_24h_pct=change24h,
            change_7d_pct=change7d,
            volatility_24h=volatility24h,
            trend=trend,
        )
        self._set_cached(cacheKey, analysis)
        logging.info(f'Price analysis for {assetAddress}: {analysis.to_summary()}')
        return analysis
