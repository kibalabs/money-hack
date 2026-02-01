import { dateFromString } from '@kibalabs/core';

import { RawObject } from './endpoints';

export class CollateralAsset {
  public constructor(
    readonly chainId: number,
    readonly address: string,
    readonly symbol: string,
    readonly name: string,
    readonly decimals: number,
    readonly logoUri: string | null,
  ) { }

  public static fromObject = (obj: RawObject): CollateralAsset => {
    return new CollateralAsset(
      Number(obj.chain_id),
      String(obj.address),
      String(obj.symbol),
      String(obj.name),
      Number(obj.decimals),
      obj.logo_uri ? String(obj.logo_uri) : null,
    );
  };
}

export class Position {
  public constructor(
    readonly positionId: string,
    readonly createdDate: Date,
    readonly userAddress: string,
    readonly collateralAsset: CollateralAsset,
    readonly collateralAmount: bigint,
    readonly collateralValueUsd: number,
    readonly borrowAmount: bigint,
    readonly borrowValueUsd: number,
    readonly currentLtv: number,
    readonly targetLtv: number,
    readonly healthFactor: number,
    readonly vaultBalance: bigint,
    readonly vaultBalanceUsd: number,
    readonly accruedYield: bigint,
    readonly accruedYieldUsd: number,
    readonly estimatedApy: number,
    readonly status: string,
  ) { }

  public static fromObject = (obj: RawObject): Position => {
    return new Position(
      String(obj.position_id),
      dateFromString(String(obj.created_date)),
      String(obj.user_address),
      CollateralAsset.fromObject(obj.collateral_asset as RawObject),
      BigInt(obj.collateral_amount as string),
      Number(obj.collateral_value_usd),
      BigInt(obj.borrow_amount as string),
      Number(obj.borrow_value_usd),
      Number(obj.current_ltv),
      Number(obj.target_ltv),
      Number(obj.health_factor),
      BigInt(obj.vault_balance as string),
      Number(obj.vault_balance_usd),
      BigInt(obj.accrued_yield as string),
      Number(obj.accrued_yield_usd),
      Number(obj.estimated_apy),
      String(obj.status),
    );
  };
}

export class UserConfig {
  public constructor(
    readonly telegramHandle: string | null,
    readonly preferredLtv: number,
  ) { }

  public static fromObject = (obj: RawObject): UserConfig => {
    return new UserConfig(
      obj.telegram_handle ? String(obj.telegram_handle) : null,
      Number(obj.preferred_ltv),
    );
  };
}

export class CollateralMarketData {
  public constructor(
    readonly collateralAddress: string,
    readonly collateralSymbol: string,
    readonly borrowApy: number,
    readonly maxLtv: number,
    readonly marketId: string | null,
  ) { }

  public static fromObject = (obj: RawObject): CollateralMarketData => {
    return new CollateralMarketData(
      String(obj.collateral_address),
      String(obj.collateral_symbol),
      Number(obj.borrow_apy),
      Number(obj.max_ltv),
      obj.market_id ? String(obj.market_id) : null,
    );
  };
}

export class MarketData {
  public constructor(
    readonly collateralMarkets: CollateralMarketData[],
    readonly yieldApy: number,
    readonly yieldVaultAddress: string,
    readonly yieldVaultName: string,
  ) { }

  public static fromObject = (obj: RawObject): MarketData => {
    return new MarketData(
      (obj.collateral_markets as RawObject[]).map(CollateralMarketData.fromObject),
      Number(obj.yield_apy),
      String(obj.yield_vault_address),
      String(obj.yield_vault_name),
    );
  };
}

export class AssetBalance {
  public constructor(
    readonly assetAddress: string,
    readonly assetSymbol: string,
    readonly assetDecimals: number,
    readonly balance: bigint,
    readonly balanceUsd: number,
  ) { }

  public static fromObject = (obj: RawObject): AssetBalance => {
    return new AssetBalance(
      String(obj.asset_address),
      String(obj.asset_symbol),
      Number(obj.asset_decimals),
      BigInt(obj.balance as string),
      Number(obj.balance_usd),
    );
  };
}

export class Wallet {
  public constructor(
    readonly walletAddress: string,
    readonly assetBalances: AssetBalance[],
  ) { }

  public static fromObject = (obj: RawObject): Wallet => {
    return new Wallet(
      String(obj.wallet_address),
      (obj.asset_balances as RawObject[]).map(AssetBalance.fromObject),
    );
  };
}
