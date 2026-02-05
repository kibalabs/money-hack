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

export class GetAgentRequest extends RequestData {
  public constructor() {
    super();
  }

  public toObject = (): RawObject => {
    return {};
  };
}

export class GetAgentResponse extends ResponseData {
  public constructor(
    readonly agent: Resources.Agent | null,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetAgentResponse => {
    return new GetAgentResponse(
      obj.agent ? Resources.Agent.fromObject(obj.agent as RawObject) : null,
    );
  };
}

export class CreateAgentRequest extends RequestData {
  public constructor(
    readonly name: string,
    readonly emoji: string,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      name: this.name,
      emoji: this.emoji,
    };
  };
}

export class CreateAgentResponse extends ResponseData {
  public constructor(
    readonly agent: Resources.Agent,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): CreateAgentResponse => {
    return new CreateAgentResponse(
      Resources.Agent.fromObject(obj.agent as RawObject),
    );
  };
}

export class DeployAgentRequest extends RequestData {
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

export class DeployAgentResponse extends ResponseData {
  public constructor(
    readonly position: Resources.Position,
    readonly transactionHash: string | null,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): DeployAgentResponse => {
    return new DeployAgentResponse(
      Resources.Position.fromObject(obj.position as RawObject),
      obj.transaction_hash ? String(obj.transaction_hash) : null,
    );
  };
}

export class SendChatMessageRequest extends RequestData {
  public constructor(
    readonly message: string,
    readonly conversationId: string | null,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      message: this.message,
      conversation_id: this.conversationId,
    };
  };
}

export class SendChatMessageResponse extends ResponseData {
  public constructor(
    readonly messages: Resources.ChatMessage[],
    readonly conversationId: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): SendChatMessageResponse => {
    return new SendChatMessageResponse(
      (obj.messages as RawObject[]).map(Resources.ChatMessage.fromObject),
      String(obj.conversation_id),
    );
  };
}

export class GetChatHistoryRequest extends RequestData {
  public constructor(
    readonly conversationId: string | null,
    readonly limit: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      conversation_id: this.conversationId,
      limit: this.limit,
    };
  };
}

export class GetChatHistoryResponse extends ResponseData {
  public constructor(
    readonly messages: Resources.ChatMessage[],
    readonly conversationId: string,
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetChatHistoryResponse => {
    return new GetChatHistoryResponse(
      (obj.messages as RawObject[]).map(Resources.ChatMessage.fromObject),
      String(obj.conversation_id),
    );
  };
}

export class GetAgentThoughtsRequest extends RequestData {
  public constructor(
    readonly limit: number,
    readonly hoursBack: number,
  ) {
    super();
  }

  public toObject = (): RawObject => {
    return {
      limit: this.limit,
      hours_back: this.hoursBack,
    };
  };
}

export class GetAgentThoughtsResponse extends ResponseData {
  public constructor(
    readonly actions: Resources.AgentAction[],
  ) {
    super();
  }

  public static fromObject = (obj: RawObject): GetAgentThoughtsResponse => {
    return new GetAgentThoughtsResponse(
      (obj.actions as RawObject[]).map(Resources.AgentAction.fromObject),
    );
  };
}
