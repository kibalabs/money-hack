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

export class GetWalletRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetWalletResponse extends ResponseData {
  public constructor(
    readonly wallet: Resources.Wallet,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetWalletResponse => {
    return new GetWalletResponse(
      Resources.Wallet.fromObject(obj.wallet as RawObject),
    );
  };
}

export class GetPositionTransactionsRequest extends RequestData {
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

export class GetPositionTransactionsResponse extends ResponseData {
  public constructor(
    readonly positionTransactions: Resources.PositionTransactions,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetPositionTransactionsResponse => {
    return new GetPositionTransactionsResponse(
      Resources.PositionTransactions.fromObject(obj as RawObject),
    );
  };
}

export class TelegramLoginUrlRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class TelegramLoginUrlResponse extends ResponseData {
  public constructor(
    readonly loginUrl: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): TelegramLoginUrlResponse => {
    return new TelegramLoginUrlResponse(
      String(obj.login_url),
    );
  };
}

export class VerifyTelegramCodeRequest extends RequestData {
  public constructor(
    readonly secretCode: string,
    readonly authData: Record<string, string | null>,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      secret_code: this.secretCode,
      auth_data: this.authData,
    };
  };
}

export class VerifyTelegramCodeResponse extends ResponseData {
  public constructor(
    readonly userConfig: Resources.UserConfig,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): VerifyTelegramCodeResponse => {
    return new VerifyTelegramCodeResponse(
      Resources.UserConfig.fromObject(obj.user_config as RawObject),
    );
  };
}

export class DisconnectTelegramRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class DisconnectTelegramResponse extends ResponseData {
  public constructor(
    readonly userConfig: Resources.UserConfig,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): DisconnectTelegramResponse => {
    return new DisconnectTelegramResponse(
      Resources.UserConfig.fromObject(obj.user_config as RawObject),
    );
  };
}
