# Query for getting market (lending pool) data including borrow rates
# Markets represent lending pools where you can supply collateral and borrow assets
LIST_MARKETS_QUERY = """
query ListMarkets($skip: Int!, $chainId: Int!, $collateralAssetAddress: String!, $loanAssetAddress: String!) {
  markets(first: 100, skip: $skip, where: {chainId_in: [$chainId], collateralAssetAddress_in: [$collateralAssetAddress], loanAssetAddress_in: [$loanAssetAddress]}) {
    items {
      uniqueKey
      lltv
      collateralAsset {
        address
        symbol
        decimals
      }
      loanAsset {
        address
        symbol
        decimals
      }
      state {
        borrowApy
        supplyApy
        utilization
        supplyAssets
        borrowAssets
      }
      oracleInfo {
        type
      }
    }
    pageInfo {
      countTotal
      count
      limit
      skip
    }
  }
}
"""

# Query for getting all markets for a specific loan asset (e.g., all USDC borrowing markets)
LIST_MARKETS_BY_LOAN_ASSET_QUERY = """
query ListMarketsByLoanAsset($skip: Int!, $chainId: Int!, $loanAssetAddress: String!) {
  markets(first: 100, skip: $skip, where: {chainId_in: [$chainId], loanAssetAddress_in: [$loanAssetAddress]}) {
    items {
      uniqueKey
      lltv
      collateralAsset {
        address
        symbol
        decimals
      }
      loanAsset {
        address
        symbol
        decimals
      }
      state {
        borrowApy
        supplyApy
        utilization
        supplyAssets
        borrowAssets
      }
      oracleInfo {
        type
      }
    }
    pageInfo {
      countTotal
      count
      limit
      skip
    }
  }
}
"""
