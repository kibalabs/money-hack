from core.api.api_request import KibaApiRequest
from core.api.json_route import json_route
from starlette.routing import Route

from money_hack.agent_manager import AgentManager
from money_hack.api import v1_resources as resources
from money_hack.api.authorizer import authorize_signature


def create_v1_routes(agentManager: AgentManager) -> list[Route]:
    @json_route(requestType=resources.EmptyRequest, responseType=resources.GetSupportedCollateralsResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_supported_collaterals(request: KibaApiRequest[resources.EmptyRequest]) -> resources.GetSupportedCollateralsResponse:  # noqa: ARG001
        collaterals = await agentManager.get_supported_collaterals()
        return resources.GetSupportedCollateralsResponse(collaterals=collaterals)

    @json_route(requestType=resources.EmptyRequest, responseType=resources.GetUserConfigResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_user_config(request: KibaApiRequest[resources.EmptyRequest]) -> resources.GetUserConfigResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.get_user_config(user_address=userAddress)
        return resources.GetUserConfigResponse(user_config=user_config)

    @json_route(requestType=resources.UpdateUserConfigRequest, responseType=resources.UpdateUserConfigResponse)
    @authorize_signature(authorizer=agentManager)
    async def update_user_config(request: KibaApiRequest[resources.UpdateUserConfigRequest]) -> resources.UpdateUserConfigResponse:
        userAddress = request.path_params.get('userAddress', '')
        user_config = await agentManager.update_user_config(user_address=userAddress, telegram_handle=request.data.telegram_handle, preferred_ltv=request.data.preferred_ltv)
        return resources.UpdateUserConfigResponse(user_config=user_config)

    @json_route(requestType=resources.EmptyRequest, responseType=resources.GetPositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def get_position(request: KibaApiRequest[resources.EmptyRequest]) -> resources.GetPositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        position = await agentManager.get_position(user_address=userAddress)
        return resources.GetPositionResponse(position=position)

    @json_route(requestType=resources.CreatePositionRequest, responseType=resources.CreatePositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def create_position(request: KibaApiRequest[resources.CreatePositionRequest]) -> resources.CreatePositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        position = await agentManager.create_position(user_address=userAddress, collateral_asset_address=request.data.collateral_asset_address, collateral_amount=request.data.collateral_amount, target_ltv=request.data.target_ltv)
        return resources.CreatePositionResponse(position=position)

    @json_route(requestType=resources.WithdrawRequest, responseType=resources.WithdrawResponse)
    @authorize_signature(authorizer=agentManager)
    async def withdraw_usdc(request: KibaApiRequest[resources.WithdrawRequest]) -> resources.WithdrawResponse:
        userAddress = request.path_params.get('userAddress', '')
        position, transaction_hash = await agentManager.withdraw_usdc(user_address=userAddress, amount=request.data.amount)
        return resources.WithdrawResponse(position=position, transaction_hash=transaction_hash)

    @json_route(requestType=resources.EmptyRequest, responseType=resources.ClosePositionResponse)
    @authorize_signature(authorizer=agentManager)
    async def close_position(request: KibaApiRequest[resources.EmptyRequest]) -> resources.ClosePositionResponse:
        userAddress = request.path_params.get('userAddress', '')
        transaction_hash = await agentManager.close_position(user_address=userAddress)
        return resources.ClosePositionResponse(transaction_hash=transaction_hash)

    @json_route(requestType=resources.EmptyRequest, responseType=resources.MarketDataResponse)
    async def get_market_data(request: KibaApiRequest[resources.EmptyRequest]) -> resources.MarketDataResponse:  # noqa: ARG001
        collateralMarkets, yieldApy, vaultAddress, vaultName = await agentManager.get_market_data()
        return resources.MarketDataResponse(collateral_markets=collateralMarkets, yield_apy=yieldApy, yield_vault_address=vaultAddress, yield_vault_name=vaultName)

    return [
        Route('/v1/collaterals', endpoint=get_supported_collaterals, methods=['GET']),
        Route('/v1/market-data', endpoint=get_market_data, methods=['GET']),
        Route('/v1/users/{userAddress:str}/config', endpoint=get_user_config, methods=['GET']),
        Route('/v1/users/{userAddress:str}/config', endpoint=update_user_config, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position', endpoint=get_position, methods=['GET']),
        Route('/v1/users/{userAddress:str}/position', endpoint=create_position, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position/withdraw', endpoint=withdraw_usdc, methods=['POST']),
        Route('/v1/users/{userAddress:str}/position/close', endpoint=close_position, methods=['POST']),
    ]
