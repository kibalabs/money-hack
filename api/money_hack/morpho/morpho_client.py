import typing

from core import logging
from core.requester import Requester
from core.util import chain_util
from pydantic import BaseModel

from money_hack import constants
from money_hack.morpho import morpho_queries


class MorphoMarket(BaseModel):
    """Represents a Morpho lending market (collateral -> loan asset pair)"""

    unique_key: str
    chain_id: int
    collateral_address: str
    collateral_symbol: str
    collateral_decimals: int
    loan_address: str
    loan_symbol: str
    loan_decimals: int
    oracle_address: str
    irm_address: str
    lltv: float  # Liquidation LTV (e.g., 0.86 = 86%)
    lltv_raw: int  # Raw LLTV value (18 decimals)
    borrow_apy: float  # Current borrow APY (e.g., 0.03 = 3%)
    supply_apy: float  # Current supply APY
    utilization: float  # Current utilization rate
    total_supply: int  # Total supplied assets (raw)
    total_borrow: int  # Total borrowed assets (raw)


class MorphoClient:
    """Client for fetching Morpho lending market data (borrow rates, etc.)"""

    GRAPHQL_URL = 'https://blue-api.morpho.org/graphql'

    def __init__(self, requester: Requester) -> None:
        self.requester = requester

    async def _query_graphql(self, query: str, variables: dict[str, typing.Any]) -> dict[str, typing.Any]:  # type: ignore[explicit-any]
        """Execute a GraphQL query against Morpho's API"""
        response = await self.requester.post_json(
            url=self.GRAPHQL_URL,
            dataDict={
                'query': query,
                'variables': variables,
            },
            timeout=30,
        )
        return dict(response.json())

    async def get_market(
        self,
        chain_id: int,
        collateral_address: str,
        loan_address: str | None = None,
    ) -> MorphoMarket | None:
        """
        Get market data for a specific collateral/loan pair.

        Args:
            chain_id: Chain ID (e.g., 8453 for Base)
            collateral_address: Address of the collateral asset (e.g., WETH)
            loan_address: Address of the loan asset (e.g., USDC), defaults to USDC

        Returns:
            MorphoMarket with borrow rates, or None if no market exists
        """
        collateral_address = chain_util.normalize_address(collateral_address)
        if loan_address is None:
            loan_address = constants.CHAIN_USDC_MAP.get(chain_id)
            if loan_address is None:
                return None
        loan_address = chain_util.normalize_address(loan_address)

        response = await self._query_graphql(
            query=morpho_queries.LIST_MARKETS_QUERY,
            variables={
                'skip': 0,
                'chainId': chain_id,
                'collateralAssetAddress': collateral_address,
                'loanAssetAddress': loan_address,
            },
        )

        markets = response.get('data', {}).get('markets', {}).get('items', [])
        if not markets:
            logging.warning(f'No Morpho market found for {collateral_address} -> {loan_address} on chain {chain_id}')
            return None

        # Return the market with highest liquidity (most total supply)
        best_market = max(markets, key=lambda m: int(m['state']['supplyAssets'] or 0))
        return self._parse_market(best_market, chain_id)

    async def get_markets_for_collateral(
        self,
        chain_id: int,
        collateral_address: str,
        loan_address: str | None = None,
    ) -> list[MorphoMarket]:
        """
        Get all markets for a specific collateral asset.

        Args:
            chain_id: Chain ID
            collateral_address: Address of the collateral asset
            loan_address: Optional - filter to specific loan asset (e.g., USDC)

        Returns:
            List of MorphoMarket objects
        """
        collateral_address = chain_util.normalize_address(collateral_address)
        if loan_address is None:
            loan_address = constants.CHAIN_USDC_MAP.get(chain_id)
            if loan_address is None:
                return []

        loan_address = chain_util.normalize_address(loan_address)

        response = await self._query_graphql(
            query=morpho_queries.LIST_MARKETS_QUERY,
            variables={
                'skip': 0,
                'chainId': chain_id,
                'collateralAssetAddress': collateral_address,
                'loanAssetAddress': loan_address,
            },
        )

        markets = response.get('data', {}).get('markets', {}).get('items', [])
        return [self._parse_market(m, chain_id) for m in markets]

    async def get_borrow_apy(
        self,
        chain_id: int,
        collateral_address: str,
        loan_address: str | None = None,
    ) -> float | None:
        """
        Get the current borrow APY for borrowing against a collateral.

        This is the cost the user pays to borrow USDC using their collateral.

        Args:
            chain_id: Chain ID
            collateral_address: Address of the collateral asset
            loan_address: Address of the loan asset (defaults to USDC)

        Returns:
            Borrow APY as a decimal (e.g., 0.03 = 3%), or None if no market
        """
        if loan_address is None:
            loan_address = constants.CHAIN_USDC_MAP.get(chain_id)
            if loan_address is None:
                return None

        market = await self.get_market(chain_id, collateral_address, loan_address)
        if market is None:
            return None

        return market.borrow_apy

    async def get_max_ltv(
        self,
        chain_id: int,
        collateral_address: str,
        loan_address: str | None = None,
    ) -> float | None:
        """
        Get the maximum LTV (liquidation threshold) for a collateral.

        Args:
            chain_id: Chain ID
            collateral_address: Address of the collateral asset
            loan_address: Address of the loan asset (defaults to USDC)

        Returns:
            LLTV as a decimal (e.g., 0.86 = 86%), or None if no market
        """
        if loan_address is None:
            loan_address = constants.CHAIN_USDC_MAP.get(chain_id)
            if loan_address is None:
                return None

        market = await self.get_market(chain_id, collateral_address, loan_address)
        if market is None:
            return None

        return market.lltv

    def _parse_market(self, market_dict: dict[str, typing.Any], chain_id: int) -> MorphoMarket:  # type: ignore[explicit-any]
        """Parse a market dict from GraphQL response into MorphoMarket"""
        state = market_dict.get('state', {})
        collateral = market_dict.get('collateralAsset', {})
        loan = market_dict.get('loanAsset', {})
        rawLltv = float(market_dict.get('lltv', 0))
        lltvRaw = int(rawLltv) if rawLltv > 1 else int(rawLltv * 1e18)
        lltv = rawLltv / 1e18 if rawLltv > 1 else rawLltv
        return MorphoMarket(
            unique_key=market_dict.get('uniqueKey', ''),
            chain_id=chain_id,
            collateral_address=chain_util.normalize_address(collateral.get('address', '')),
            collateral_symbol=collateral.get('symbol', ''),
            collateral_decimals=int(collateral.get('decimals', 18)),
            loan_address=chain_util.normalize_address(loan.get('address', '')),
            loan_symbol=loan.get('symbol', ''),
            loan_decimals=int(loan.get('decimals', 6)),
            oracle_address=chain_util.normalize_address(market_dict.get('oracleAddress', '')),
            irm_address=chain_util.normalize_address(market_dict.get('irmAddress', '')),
            lltv=lltv,
            lltv_raw=lltvRaw,
            borrow_apy=float(state.get('borrowApy', 0) or 0),
            supply_apy=float(state.get('supplyApy', 0) or 0),
            utilization=float(state.get('utilization', 0) or 0),
            total_supply=int(state.get('supplyAssets', 0) or 0),
            total_borrow=int(state.get('borrowAssets', 0) or 0),
        )
