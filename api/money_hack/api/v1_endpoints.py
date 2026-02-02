from pydantic import BaseModel

from money_hack.api import v1_resources as resources
from money_hack.external.telegram_client import TelegramAuthData


class GetSupportedCollateralsRequest(BaseModel):
    pass


class GetSupportedCollateralsResponse(BaseModel):
    collaterals: list[resources.CollateralAsset]


class GetUserConfigRequest(BaseModel):
    pass


class GetUserConfigResponse(BaseModel):
    user_config: resources.UserConfig


class UpdateUserConfigRequest(BaseModel):
    telegram_handle: str | None = None
    preferred_ltv: float | None = None


class UpdateUserConfigResponse(BaseModel):
    user_config: resources.UserConfig


class GetPositionRequest(BaseModel):
    pass


class GetPositionResponse(BaseModel):
    position: resources.Position | None


class CreatePositionRequest(BaseModel):
    collateral_asset_address: str
    collateral_amount: str
    target_ltv: float


class CreatePositionResponse(BaseModel):
    position: resources.Position


class WithdrawRequest(BaseModel):
    amount: str


class WithdrawResponse(BaseModel):
    position: resources.Position
    transaction_hash: str


class ClosePositionRequest(BaseModel):
    pass


class ClosePositionResponse(BaseModel):
    transaction_hash: str


class GetMarketDataRequest(BaseModel):
    pass


class GetMarketDataResponse(BaseModel):
    collateral_markets: list[resources.CollateralMarketData]
    yield_apy: float
    yield_vault_address: str
    yield_vault_name: str


class GetWalletRequest(BaseModel):
    pass


class GetWalletResponse(BaseModel):
    wallet: resources.Wallet


class GetPositionTransactionsRequest(BaseModel):
    collateral_asset_address: str
    collateral_amount: str
    target_ltv: float


class GetPositionTransactionsResponse(BaseModel):
    transactions: list[resources.TransactionCall]
    morpho_address: str
    vault_address: str
    estimated_borrow_amount: str
    needs_approval: bool


class GetTelegramLoginUrlRequest(BaseModel):
    pass


class GetTelegramLoginUrlResponse(BaseModel):
    login_url: str
    secret_code: str


class VerifyTelegramCodeRequest(BaseModel):
    secret_code: str
    auth_data: TelegramAuthData


class VerifyTelegramCodeResponse(BaseModel):
    user_config: resources.UserConfig


class DisconnectTelegramRequest(BaseModel):
    pass


class DisconnectTelegramResponse(BaseModel):
    user_config: resources.UserConfig
