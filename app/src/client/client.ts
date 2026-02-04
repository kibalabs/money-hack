import { RestMethod, ServiceClient } from '@kibalabs/core';

import * as Endpoints from './endpoints';
import * as Resources from './resources';

export class MoneyHackClient extends ServiceClient {
  // eslint-disable-next-line class-methods-use-this
  private getHeaders = (authToken: string | null = null): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (authToken) {
      headers.Authorization = `Signature ${authToken}`;
    }
    return headers;
  };

  public getSupportedCollaterals = async (authToken: string): Promise<Resources.CollateralAsset[]> => {
    const method = RestMethod.GET;
    const path = 'v1/collaterals';
    const request = new Endpoints.GetSupportedCollateralsRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.GetSupportedCollateralsResponse, this.getHeaders(authToken));
    return response.collaterals;
  };

  public getUserConfig = async (userAddress: string, authToken: string): Promise<Resources.UserConfig> => {
    const method = RestMethod.GET;
    const path = `v1/users/${userAddress}/config`;
    const request = new Endpoints.GetUserConfigRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.GetUserConfigResponse, this.getHeaders(authToken));
    return response.userConfig;
  };

  public updateUserConfig = async (userAddress: string, telegramHandle: string | null, preferredLtv: number, authToken: string): Promise<Resources.UserConfig> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/config`;
    const request = new Endpoints.UpdateUserConfigRequest(telegramHandle, preferredLtv);
    const response = await this.makeRequest(method, path, request, Endpoints.UpdateUserConfigResponse, this.getHeaders(authToken));
    return response.userConfig;
  };

  public createPosition = async (userAddress: string, collateralAssetAddress: string, collateralAmount: bigint, targetLtv: number, agentName: string, agentEmoji: string, authToken: string): Promise<Resources.CreatePositionResult> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/positions`;
    const request = new Endpoints.CreatePositionRequest(collateralAssetAddress, collateralAmount.toString(), targetLtv, agentName, agentEmoji);
    const response = await this.makeRequest(method, path, request, Endpoints.CreatePositionResponse, this.getHeaders(authToken));
    return new Resources.CreatePositionResult(response.position, response.agent);
  };

  public getPosition = async (userAddress: string, authToken: string): Promise<Resources.Position | null> => {
    const method = RestMethod.GET;
    const path = `v1/users/${userAddress}/position`;
    const request = new Endpoints.GetPositionRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.GetPositionResponse, this.getHeaders(authToken));
    return response.position;
  };

  public getWithdrawTransactions = async (userAddress: string, amount: bigint, authToken: string): Promise<Endpoints.WithdrawResponse> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/position/withdraw`;
    const request = new Endpoints.WithdrawRequest(amount.toString());
    const response = await this.makeRequest(method, path, request, Endpoints.WithdrawResponse, this.getHeaders(authToken));
    return response;
  };

  public getClosePositionTransactions = async (userAddress: string, authToken: string): Promise<Endpoints.ClosePositionResponse> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/position/close`;
    const request = new Endpoints.ClosePositionRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.ClosePositionResponse, this.getHeaders(authToken));
    return response;
  };

  public getMarketData = async (): Promise<Resources.MarketData> => {
    const method = RestMethod.GET;
    const path = 'v1/market-data';
    const request = new Endpoints.GetMarketDataRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.GetMarketDataResponse, this.getHeaders(null));
    return response.marketData;
  };

  public getWallet = async (walletAddress: string, authToken: string): Promise<Resources.Wallet> => {
    const method = RestMethod.GET;
    const path = `v1/wallets/${walletAddress}`;
    const request = new Endpoints.GetWalletRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.GetWalletResponse, this.getHeaders(authToken));
    return response.wallet;
  };

  public getPositionTransactions = async (userAddress: string, collateralAssetAddress: string, collateralAmount: bigint, targetLtv: number, authToken: string): Promise<Resources.PositionTransactions> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/position/transactions`;
    const request = new Endpoints.GetPositionTransactionsRequest(collateralAssetAddress, collateralAmount.toString(), targetLtv);
    const response = await this.makeRequest(method, path, request, Endpoints.GetPositionTransactionsResponse, this.getHeaders(authToken));
    return response.positionTransactions;
  };

  public getTelegramBotUsername = async (userAddress: string, authToken: string): Promise<string> => {
    const method = RestMethod.GET;
    const path = `v1/users/${userAddress}/telegram/login-url`;
    const request = new Endpoints.TelegramLoginUrlRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.TelegramLoginUrlResponse, this.getHeaders(authToken));
    return response.botUsername;
  };

  public telegramSecretVerify = async (userAddress: string, telegramSecret: string, authToken: string): Promise<Resources.UserConfig> => {
    const method = RestMethod.POST;
    const path = `v1/users/${userAddress}/telegram/secret-verify`;
    const request = new Endpoints.TelegramSecretVerifyRequest(telegramSecret);
    const response = await this.makeRequest(method, path, request, Endpoints.TelegramSecretVerifyResponse, this.getHeaders(authToken));
    return response.userConfig;
  };

  public disconnectTelegram = async (userAddress: string, authToken: string): Promise<Resources.UserConfig> => {
    const method = RestMethod.DELETE;
    const path = `v1/users/${userAddress}/telegram`;
    const request = new Endpoints.DisconnectTelegramRequest();
    const response = await this.makeRequest(method, path, request, Endpoints.DisconnectTelegramResponse, this.getHeaders(authToken));
    return response.userConfig;
  };
}
