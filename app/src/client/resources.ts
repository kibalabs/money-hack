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
      Number(obj.chainId),
      String(obj.address),
      String(obj.symbol),
      String(obj.name),
      Number(obj.decimals),
      obj.logoUri ? String(obj.logoUri) : null,
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
      String(obj.positionId),
      dateFromString(String(obj.createdDate)),
      String(obj.userAddress),
      CollateralAsset.fromObject(obj.collateralAsset as RawObject),
      BigInt(obj.collateralAmount as string),
      Number(obj.collateralValueUsd),
      BigInt(obj.borrowAmount as string),
      Number(obj.borrowValueUsd),
      Number(obj.currentLtv),
      Number(obj.targetLtv),
      Number(obj.healthFactor),
      BigInt(obj.vaultBalance as string),
      Number(obj.vaultBalanceUsd),
      BigInt(obj.accruedYield as string),
      Number(obj.accruedYieldUsd),
      Number(obj.estimatedApy),
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
      obj.telegramHandle ? String(obj.telegramHandle) : null,
      Number(obj.preferredLtv),
    );
  };
}
