from datetime import datetime

from pydantic import BaseModel


class EmptyRequest(BaseModel):
    pass


class AuthToken(BaseModel):
    message: str
    signature: str


class CollateralAsset(BaseModel):
    chain_id: int
    address: str
    symbol: str
    name: str
    decimals: int
    logo_uri: str | None


class Position(BaseModel):
    position_id: str
    created_date: datetime
    user_address: str
    collateral_asset: CollateralAsset
    collateral_amount: str
    collateral_value_usd: float
    borrow_amount: str
    borrow_value_usd: float
    current_ltv: float
    target_ltv: float
    health_factor: float
    vault_balance: str
    vault_balance_usd: float
    accrued_yield: str
    accrued_yield_usd: float
    estimated_apy: float
    status: str


class UserConfig(BaseModel):
    telegram_handle: str | None
    preferred_ltv: float


class GetSupportedCollateralsResponse(BaseModel):
    collaterals: list[CollateralAsset]


class GetUserConfigResponse(BaseModel):
    user_config: UserConfig


class UpdateUserConfigRequest(BaseModel):
    telegram_handle: str | None
    preferred_ltv: float


class UpdateUserConfigResponse(BaseModel):
    user_config: UserConfig


class CreatePositionRequest(BaseModel):
    collateral_asset_address: str
    collateral_amount: str
    target_ltv: float


class CreatePositionResponse(BaseModel):
    position: Position


class GetPositionResponse(BaseModel):
    position: Position | None


class WithdrawRequest(BaseModel):
    amount: str


class WithdrawResponse(BaseModel):
    position: Position
    transaction_hash: str


class ClosePositionResponse(BaseModel):
    transaction_hash: str


class CollateralMarketData(BaseModel):
    collateral_address: str
    collateral_symbol: str
    borrow_apy: float
    max_ltv: float
    market_id: str | None


class MarketDataResponse(BaseModel):
    collateral_markets: list[CollateralMarketData]
    yield_apy: float
    yield_vault_address: str
    yield_vault_name: str
