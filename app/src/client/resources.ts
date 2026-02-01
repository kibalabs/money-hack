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
