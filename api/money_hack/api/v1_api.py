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
        position = await agentManager.create_position(user_address=userAddress, collateral_asset_address=request.data.collateral_asset_address, collateral_amount=request.data.collateral_amount, target_ltv=request.data.target_ltv)
        return endpoints.CreatePositionResponse(position=position)

    @json_route(requestType=endpoints.WithdrawRequest, responseType=endpoints.WithdrawResponse)
    @authorize_signature(authorizer=agentManager)
    async def withdraw_usdc(request: KibaApiRequest[endpoints.WithdrawRequest]) -> endpoints.WithdrawResponse:
        userAddress = request.path_params.get('userAddress', '')
        position, transaction_hash = await agentManager.withdraw_usdc(user_address=userAddress, amount=request.data.amount)
        return endpoints.WithdrawResponse(position=position, transaction_hash=transaction_hash)

    @json_route(requestType=endpoints.ClosePositionRequest, responseType=endpoints.ClosePositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def close_position(request: KibaApiRequest[endpoints.ClosePositionRequest]) -> endpoints.ClosePositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        transaction_hash = await agentManager.close_position(user_address=userAddress)
        return endpoints.ClosePositionResponse(transaction_hash=transaction_hash)

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
    async def get_telegram_login_url(request: KibaApiRequest[endpoints.GetTelegramLoginUrlRequest]) -> endpoints.GetTelegramLoginUrlResponse:
        userAddress = request.path_params.get('userAddress', '')
        loginUrl, secretCode = await agentManager.get_telegram_login_url(user_address=userAddress)
        return endpoints.GetTelegramLoginUrlResponse(login_url=loginUrl, secret_code=secretCode)

    @json_route(requestType=endpoints.VerifyTelegramCodeRequest, responseType=endpoints.VerifyTelegramCodeResponse)
    @authorize_signature(authorizer=agentManager)
    async def verify_telegram_code(request: KibaApiRequest[endpoints.VerifyTelegramCodeRequest]) -> endpoints.VerifyTelegramCodeResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.verify_telegram_code(
            user_address=userAddress,
            secretCode=request.data.secret_code,
            authData=request.data.auth_data,
        )
        return endpoints.VerifyTelegramCodeResponse(user_config=user_config)

    @json_route(requestType=endpoints.DisconnectTelegramRequest, responseType=endpoints.DisconnectTelegramResponse)
    @authorize_signature(authorizer=agentManager)
    async def disconnect_telegram(request: KibaApiRequest[endpoints.DisconnectTelegramRequest]) -> endpoints.DisconnectTelegramResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.disconnect_telegram(user_address=userAddress)
        return endpoints.DisconnectTelegramResponse(user_config=user_config)

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
        Route('/v1/users/{userAddress:str}/telegram/verify-code', endpoint=verify_telegram_code, methods=['POST']),
        Route('/v1/users/{userAddress:str}/telegram', endpoint=disconnect_telegram, methods=['DELETE']),
    ]
