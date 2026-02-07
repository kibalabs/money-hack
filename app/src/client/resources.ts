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
    readonly walletCollateralBalance: bigint,
    readonly walletCollateralBalanceUsd: number,
    readonly walletUsdcBalance: bigint,
    readonly walletUsdcBalanceUsd: number,
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
      BigInt(obj.wallet_collateral_balance as string),
      Number(obj.wallet_collateral_balance_usd),
      BigInt(obj.wallet_usdc_balance as string),
      Number(obj.wallet_usdc_balance_usd),
    );
  };
}

export class UserConfig {
  public constructor(
    readonly telegramHandle: string | null,
    readonly telegramChatId: string | number | null,
    readonly preferredLtv: number,
  ) { }

  public static fromObject = (obj: RawObject): UserConfig => {
    return new UserConfig(
      obj.telegram_handle ? String(obj.telegram_handle) : null,
      obj.telegram_chat_id ? (typeof obj.telegram_chat_id === 'string' ? obj.telegram_chat_id : String(obj.telegram_chat_id)) : null,
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

export class TransactionCall {
  public constructor(
    readonly to: string,
    readonly data: string,
    readonly value: string,
  ) { }

  public static fromObject = (obj: RawObject): TransactionCall => {
    return new TransactionCall(
      String(obj.to),
      String(obj.data),
      String(obj.value || '0'),
    );
  };
}

export class WithdrawPreview {
  public constructor(
    readonly withdrawAmount: bigint,
    readonly vaultBalance: bigint,
    readonly maxSafeWithdraw: bigint,
    readonly currentLtv: number,
    readonly estimatedNewLtv: number,
    readonly targetLtv: number,
    readonly maxLtv: number,
    readonly hardMaxLtv: number,
    readonly isWarning: boolean,
    readonly isBlocked: boolean,
    readonly warningMessage: string | null,
  ) { }

  public static fromObject = (obj: RawObject): WithdrawPreview => {
    return new WithdrawPreview(
      BigInt(obj.withdraw_amount as string),
      BigInt(obj.vault_balance as string),
      BigInt(obj.max_safe_withdraw as string),
      Number(obj.current_ltv),
      Number(obj.estimated_new_ltv),
      Number(obj.target_ltv),
      Number(obj.max_ltv),
      Number(obj.hard_max_ltv),
      Boolean(obj.is_warning),
      Boolean(obj.is_blocked),
      obj.warning_message ? String(obj.warning_message) : null,
    );
  };
}

export class PositionTransactions {
  public constructor(
    readonly transactions: TransactionCall[],
    readonly morphoAddress: string,
    readonly vaultAddress: string,
    readonly estimatedBorrowAmount: bigint,
    readonly needsApproval: boolean,
  ) { }

  public static fromObject = (obj: RawObject): PositionTransactions => {
    return new PositionTransactions(
      (obj.transactions as RawObject[]).map(TransactionCall.fromObject),
      String(obj.morpho_address),
      String(obj.vault_address),
      BigInt(obj.estimated_borrow_amount as string),
      Boolean(obj.needs_approval),
    );
  };
}

export class Agent {
  public constructor(
    readonly agentId: string,
    readonly name: string,
    readonly emoji: string,
    readonly agentIndex: number,
    readonly walletAddress: string,
    readonly ensName: string | null,
    readonly createdDate: Date,
  ) { }

  public static fromObject = (obj: RawObject): Agent => {
    return new Agent(
      String(obj.agent_id),
      String(obj.name),
      String(obj.emoji),
      Number(obj.agent_index),
      String(obj.wallet_address),
      obj.ens_name ? String(obj.ens_name) : null,
      dateFromString(String(obj.created_date)),
    );
  };
}

export class CreatePositionResult {
  public constructor(
    readonly position: Position,
    readonly agent: Agent,
  ) { }

  public static fromObject = (obj: RawObject): CreatePositionResult => {
    return new CreatePositionResult(
      Position.fromObject(obj.position as RawObject),
      Agent.fromObject(obj.agent as RawObject),
    );
  };
}

export class DeployAgentResult {
  public constructor(
    readonly position: Position,
    readonly transactionHash: string | null,
  ) { }

  public static fromObject = (obj: RawObject): DeployAgentResult => {
    return new DeployAgentResult(
      Position.fromObject(obj.position as RawObject),
      obj.transaction_hash ? String(obj.transaction_hash) : null,
    );
  };
}

export class ChatMessage {
  public constructor(
    readonly messageId: number,
    readonly createdDate: Date,
    readonly isUser: boolean,
    readonly content: string,
  ) { }

  public static fromObject = (obj: RawObject): ChatMessage => {
    return new ChatMessage(
      Number(obj.message_id),
      dateFromString(String(obj.created_date)),
      Boolean(obj.is_user),
      String(obj.content),
    );
  };
}

export class ChatResponse {
  public constructor(
    readonly messages: ChatMessage[],
    readonly conversationId: string,
  ) { }

  public static fromObject = (obj: RawObject): ChatResponse => {
    return new ChatResponse(
      (obj.messages as RawObject[]).map(ChatMessage.fromObject),
      String(obj.conversation_id),
    );
  };
}

export class AgentAction {
  public constructor(
    readonly actionId: number,
    readonly createdDate: Date,
    readonly agentId: string,
    readonly actionType: string,
    readonly value: string,
    readonly details: Record<string, unknown>,
  ) { }

  public static fromObject = (obj: RawObject): AgentAction => {
    return new AgentAction(
      Number(obj.action_id),
      dateFromString(String(obj.created_date)),
      String(obj.agent_id),
      String(obj.action_type),
      String(obj.value),
      obj.details as Record<string, unknown>,
    );
  };
}
