from core.api.api_request import KibaApiRequest
from core.api.json_route import json_route
from starlette.routing import Route

from money_hack.agent_manager import AgentManager
from money_hack.api import v1_endpoints as endpoints
from money_hack.api.authorizer import authorize_signature


def create_v1_routes(agentManager: AgentManager) -> list[Route]:
    @json_route(requestType=endpoints.GetSupportedCollateralsRequest, responseType=endpoints.GetSupportedCollateralsResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_supported_collaterals(request: KibaApiRequest[endpoints.GetSupportedCollateralsRequest]) -> endpoints.GetSupportedCollateralsResponse:  # noqa: ARG001
        collaterals = await agentManager.get_supported_collaterals()
        return endpoints.GetSupportedCollateralsResponse(collaterals=collaterals)

    @json_route(requestType=endpoints.GetUserConfigRequest, responseType=endpoints.GetUserConfigResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_user_config(request: KibaApiRequest[endpoints.GetUserConfigRequest]) -> endpoints.GetUserConfigResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.get_user_config(user_address=userAddress)
        return endpoints.GetUserConfigResponse(user_config=user_config)

    @json_route(requestType=endpoints.UpdateUserConfigRequest, responseType=endpoints.UpdateUserConfigResponse)
    @authorize_signature(authorizer=agentManager)
    async def update_user_config(request: KibaApiRequest[endpoints.UpdateUserConfigRequest]) -> endpoints.UpdateUserConfigResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.update_user_config(user_address=userAddress, telegram_handle=request.data.telegram_handle, preferred_ltv=request.data.preferred_ltv)
        return endpoints.UpdateUserConfigResponse(user_config=user_config)

    @json_route(requestType=endpoints.GetPositionRequest, responseType=endpoints.GetPositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_position(request: KibaApiRequest[endpoints.GetPositionRequest]) -> endpoints.GetPositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        position = await agentManager.get_position(user_address=userAddress)
        return endpoints.GetPositionResponse(position=position)

    @json_route(requestType=endpoints.CreatePositionRequest, responseType=endpoints.CreatePositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def create_position(request: KibaApiRequest[endpoints.CreatePositionRequest]) -> endpoints.CreatePositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        position, agent = await agentManager.create_position(
            user_address=userAddress,
            collateral_asset_address=request.data.collateral_asset_address,
            collateral_amount=request.data.collateral_amount,
            target_ltv=request.data.target_ltv,
            agent_name=request.data.agent_name,
            agent_emoji=request.data.agent_emoji,
        )
        return endpoints.CreatePositionResponse(position=position, agent=agent)

    @json_route(requestType=endpoints.WithdrawRequest, responseType=endpoints.WithdrawResponse)
    @authorize_signature(authorizer=agentManager)
    async def withdraw_usdc(request: KibaApiRequest[endpoints.WithdrawRequest]) -> endpoints.WithdrawResponse:
        userAddress = request.path_params.get('userAddress', '')
        withdrawData = await agentManager.get_withdraw_transactions(user_address=userAddress, amount=request.data.amount)
        return endpoints.WithdrawResponse(
            transactions=withdrawData.transactions,
            withdraw_amount=withdrawData.withdraw_amount,
            vault_address=withdrawData.vault_address,
        )

    @json_route(requestType=endpoints.ClosePositionRequest, responseType=endpoints.ClosePositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def close_position(request: KibaApiRequest[endpoints.ClosePositionRequest]) -> endpoints.ClosePositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        closeData = await agentManager.get_close_position_transactions(user_address=userAddress)
        return endpoints.ClosePositionResponse(
            transactions=closeData.transactions,
            collateral_amount=closeData.collateral_amount,
            repay_amount=closeData.repay_amount,
            vault_withdraw_amount=closeData.vault_withdraw_amount,
            morpho_address=closeData.morpho_address,
            vault_address=closeData.vault_address,
        )

    @json_route(requestType=endpoints.GetMarketDataRequest, responseType=endpoints.GetMarketDataResponse)
    async def get_market_data(request: KibaApiRequest[endpoints.GetMarketDataRequest]) -> endpoints.GetMarketDataResponse:  # noqa: ARG001
        collateralMarkets, yieldApy, vaultAddress, vaultName = await agentManager.get_market_data()
        return endpoints.GetMarketDataResponse(collateral_markets=collateralMarkets, yield_apy=yieldApy, yield_vault_address=vaultAddress, yield_vault_name=vaultName)

    @json_route(requestType=endpoints.GetWalletRequest, responseType=endpoints.GetWalletResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_wallet(request: KibaApiRequest[endpoints.GetWalletRequest]) -> endpoints.GetWalletResponse:
        walletAddress = request.path_params.get('walletAddress', '')
        wallet = await agentManager.get_wallet(wallet_address=walletAddress)
        return endpoints.GetWalletResponse(wallet=wallet)

    @json_route(requestType=endpoints.GetPositionTransactionsRequest, responseType=endpoints.GetPositionTransactionsResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_position_transactions(request: KibaApiRequest[endpoints.GetPositionTransactionsRequest]) -> endpoints.GetPositionTransactionsResponse:
        userAddress = request.path_params.get('userAddress', '')
        result = await agentManager.get_position_transactions(
            user_address=userAddress,
            collateral_asset_address=request.data.collateral_asset_address,
            collateral_amount=request.data.collateral_amount,
            target_ltv=request.data.target_ltv,
        )
        return endpoints.GetPositionTransactionsResponse(**result.model_dump())

    @json_route(requestType=endpoints.GetTelegramLoginUrlRequest, responseType=endpoints.GetTelegramLoginUrlResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_telegram_login_url(request: KibaApiRequest[endpoints.GetTelegramLoginUrlRequest]) -> endpoints.GetTelegramLoginUrlResponse:  # noqa: ARG001
        botUsername = await agentManager.get_telegram_login_url()
        return endpoints.GetTelegramLoginUrlResponse(bot_username=botUsername)

    @json_route(requestType=endpoints.TelegramSecretVerifyRequest, responseType=endpoints.TelegramSecretVerifyResponse)
    @authorize_signature(authorizer=agentManager)
    async def telegram_secret_verify(request: KibaApiRequest[endpoints.TelegramSecretVerifyRequest]) -> endpoints.TelegramSecretVerifyResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.telegram_secret_verify(
            user_address=userAddress,
            telegramSecret=request.data.telegram_secret,
        )
        return endpoints.TelegramSecretVerifyResponse(user_config=user_config)

    @json_route(requestType=endpoints.TelegramWebhookRequest, responseType=endpoints.TelegramWebhookResponse)
    async def process_telegram_webhook(request: KibaApiRequest[endpoints.TelegramWebhookRequest]) -> endpoints.TelegramWebhookResponse:
        await agentManager.process_telegram_webhook(updateDict=request.data.model_dump())
        return endpoints.TelegramWebhookResponse()

    @json_route(requestType=endpoints.DisconnectTelegramRequest, responseType=endpoints.DisconnectTelegramResponse)
    @authorize_signature(authorizer=agentManager)
    async def disconnect_telegram(request: KibaApiRequest[endpoints.DisconnectTelegramRequest]) -> endpoints.DisconnectTelegramResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.disconnect_telegram(user_address=userAddress)
        return endpoints.DisconnectTelegramResponse(user_config=user_config)

    @json_route(requestType=endpoints.CheckEnsNameRequest, responseType=endpoints.CheckEnsNameResponse)
    async def check_ens_name(request: KibaApiRequest[endpoints.CheckEnsNameRequest]) -> endpoints.CheckEnsNameResponse:
        isAvailable, fullName, error = agentManager.check_ens_name_available(label=request.data.label)
        return endpoints.CheckEnsNameResponse(label=request.data.label, full_name=fullName, available=isAvailable, error=error)

    @json_route(requestType=endpoints.GetEnsConfigTransactionsRequest, responseType=endpoints.GetEnsConfigTransactionsResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_ens_config_transactions(request: KibaApiRequest[endpoints.GetEnsConfigTransactionsRequest]) -> endpoints.GetEnsConfigTransactionsResponse:
        userAddress = request.path_params.get('userAddress', '')
        transactions, ensName = await agentManager.get_ens_config_transactions(
            userAddress=userAddress,
            collateral=request.data.collateral,
            targetLtv=request.data.target_ltv,
            maxLtv=request.data.max_ltv,
            minLtv=request.data.min_ltv,
            autoRebalance=request.data.auto_rebalance,
            riskTolerance=request.data.risk_tolerance,
            description=request.data.description,
        )
        return endpoints.GetEnsConfigTransactionsResponse(transactions=transactions, ens_name=ensName)

    return [
        Route('/v1/collaterals', endpoint=get_supported_collaterals, methods=['GET']),
        Route('/v1/market-data', endpoint=get_market_data, methods=['GET']),
        Route('/v1/wallets/{walletAddress:str}', endpoint=get_wallet, methods=['GET']),
        Route('/v1/users/{userAddress:str}/config', endpoint=get_user_config, methods=['GET']),
        Route('/v1/users/{userAddress:str}/config', endpoint=update_user_config, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position', endpoint=get_position, methods=['GET']),
        Route('/v1/users/{userAddress:str}/position', endpoint=create_position, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position/transactions', endpoint=get_position_transactions, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position/withdraw', endpoint=withdraw_usdc, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position/close', endpoint=close_position, methods=['POST']),
        Route('/v1/users/{userAddress:str}/telegram/login-url', endpoint=get_telegram_login_url, methods=['GET']),
        Route('/v1/users/{userAddress:str}/telegram/secret-verify', endpoint=telegram_secret_verify, methods=['POST']),
        Route('/v1/users/{userAddress:str}/telegram', endpoint=disconnect_telegram, methods=['DELETE']),
        Route('/v1/telegram-webhook', endpoint=process_telegram_webhook, methods=['POST']),
        Route('/v1/ens/check-name', endpoint=check_ens_name, methods=['POST']),
        Route('/v1/users/{userAddress:str}/ens/config-transactions', endpoint=get_ens_config_transactions, methods=['POST']),
    ]
