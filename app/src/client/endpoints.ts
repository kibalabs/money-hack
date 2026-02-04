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
      Resources.UserConfig.fromObject(obj.user_config as RawObject),
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
    readonly agentName: string,
    readonly agentEmoji: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      collateral_asset_address: this.collateralAssetAddress,
      collateral_amount: this.collateralAmount,
      target_ltv: this.targetLtv,
      agent_name: this.agentName,
      agent_emoji: this.agentEmoji,
    };
  };
}

export class CreatePositionResponse extends ResponseData {
  public constructor(
    readonly position: Resources.Position,
    readonly agent: Resources.Agent,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreatePositionResponse => {
    return new CreatePositionResponse(
      Resources.Position.fromObject(obj.position as RawObject),
      Resources.Agent.fromObject(obj.agent as RawObject),
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
    readonly transactions: Resources.TransactionCall[],
    readonly withdrawAmount: string,
    readonly vaultAddress: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): WithdrawResponse => {
    const transactions = (obj.transactions as RawObject[]).map(Resources.TransactionCall.fromObject);
    return new WithdrawResponse(
      transactions,
      String(obj.withdraw_amount),
      String(obj.vault_address),
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
    readonly transactions: Resources.TransactionCall[],
    readonly collateralAmount: string,
    readonly repayAmount: string,
    readonly vaultWithdrawAmount: string,
    readonly morphoAddress: string,
    readonly vaultAddress: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): ClosePositionResponse => {
    const transactions = (obj.transactions as RawObject[]).map(Resources.TransactionCall.fromObject);
    return new ClosePositionResponse(
      transactions,
      String(obj.collateral_amount),
      String(obj.repay_amount),
      String(obj.vault_withdraw_amount),
      String(obj.morpho_address),
      String(obj.vault_address),
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
      collateral_asset_address: this.collateralAssetAddress,
      collateral_amount: this.collateralAmount,
      target_ltv: this.targetLtv,
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
    readonly botUsername: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): TelegramLoginUrlResponse => {
    return new TelegramLoginUrlResponse(
      String(obj.bot_username),
    );
  };
}

export class TelegramSecretVerifyRequest extends RequestData {
  public constructor(
    readonly telegramSecret: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      telegram_secret: this.telegramSecret,
    };
  };
}

export class TelegramSecretVerifyResponse extends ResponseData {
  public constructor(
    readonly userConfig: Resources.UserConfig,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): TelegramSecretVerifyResponse => {
    return new TelegramSecretVerifyResponse(
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
