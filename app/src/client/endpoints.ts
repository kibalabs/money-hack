/* eslint-disable class-methods-use-this */
import { RequestData, ResponseData } from '@kibalabs/core';

import * as Resources from './resources';

export type RawObject = Record<string, unknown>;

export class GetSupportedCollateralsRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetSupportedCollateralsResponse extends ResponseData {
  public constructor(
    readonly collaterals: Resources.CollateralAsset[],
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetSupportedCollateralsResponse => {
    return new GetSupportedCollateralsResponse(
      (obj.collaterals as RawObject[]).map((collateral: RawObject): Resources.CollateralAsset => Resources.CollateralAsset.fromObject(collateral)),
    );
  };
}

export class GetUserConfigRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetUserConfigResponse extends ResponseData {
  public constructor(
    readonly userConfig: Resources.UserConfig,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetUserConfigResponse => {
    return new GetUserConfigResponse(
      Resources.UserConfig.fromObject(obj.userConfig as RawObject),
    );
  };
}

export class UpdateUserConfigRequest extends RequestData {
  public constructor(
    readonly telegramHandle: string | null,
    readonly preferredLtv: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      telegramHandle: this.telegramHandle,
      preferredLtv: this.preferredLtv,
    };
  };
}

export class UpdateUserConfigResponse extends ResponseData {
  public constructor(
    readonly userConfig: Resources.UserConfig,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): UpdateUserConfigResponse => {
    return new UpdateUserConfigResponse(
      Resources.UserConfig.fromObject(obj.userConfig as RawObject),
    );
  };
}

export class CreatePositionRequest extends RequestData {
  public constructor(
    readonly collateralAssetAddress: string,
    readonly collateralAmount: string,
    readonly targetLtv: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      collateralAssetAddress: this.collateralAssetAddress,
      collateralAmount: this.collateralAmount,
      targetLtv: this.targetLtv,
    };
  };
}

export class CreatePositionResponse extends ResponseData {
  public constructor(
    readonly position: Resources.Position,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreatePositionResponse => {
    return new CreatePositionResponse(
      Resources.Position.fromObject(obj.position as RawObject),
    );
  };
}

export class GetPositionRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetPositionResponse extends ResponseData {
  public constructor(
    readonly position: Resources.Position | null,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetPositionResponse => {
    return new GetPositionResponse(
      obj.position ? Resources.Position.fromObject(obj.position as RawObject) : null,
    );
  };
}

export class WithdrawRequest extends RequestData {
  public constructor(
    readonly amount: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      amount: this.amount,
    };
  };
}

export class WithdrawResponse extends ResponseData {
  public constructor(
    readonly position: Resources.Position,
    readonly transactionHash: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): WithdrawResponse => {
    return new WithdrawResponse(
      Resources.Position.fromObject(obj.position as RawObject),
      String(obj.transactionHash),
    );
  };
}

export class ClosePositionRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class ClosePositionResponse extends ResponseData {
  public constructor(
    readonly transactionHash: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): ClosePositionResponse => {
    return new ClosePositionResponse(
      String(obj.transactionHash),
    );
  };
}

export class GetMarketDataRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetMarketDataResponse extends ResponseData {
  public constructor(
    readonly marketData: Resources.MarketData,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetMarketDataResponse => {
    return new GetMarketDataResponse(
      Resources.MarketData.fromObject(obj as RawObject),
    );
  };
}
