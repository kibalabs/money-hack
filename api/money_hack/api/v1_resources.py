from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


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
    model_config = ConfigDict(populate_by_name=True)
    telegram_handle: str | None = None
    telegram_chat_id: int | str | None = None
    preferred_ltv: float | None = None


class CollateralMarketData(BaseModel):
    collateral_address: str
    collateral_symbol: str
    borrow_apy: float
    max_ltv: float
    market_id: str | None


class AssetBalance(BaseModel):
    asset_address: str
    asset_symbol: str
    asset_decimals: int
    balance: str
    balance_usd: float


class Wallet(BaseModel):
    wallet_address: str
    asset_balances: list[AssetBalance]


class TransactionCall(BaseModel):
    to: str
    data: str
    value: str = '0'


class PositionTransactionsData(BaseModel):
    transactions: list[TransactionCall]
    morpho_address: str
    vault_address: str
    estimated_borrow_amount: str
    needs_approval: bool


class WithdrawTransactionsData(BaseModel):
    transactions: list[TransactionCall]
    withdraw_amount: str
    vault_address: str


class ClosePositionTransactionsData(BaseModel):
    transactions: list[TransactionCall]
    collateral_amount: str
    repay_amount: str
    vault_withdraw_amount: str
    morpho_address: str
    vault_address: str


class Agent(BaseModel):
    agent_id: str
    name: str
    emoji: str
    agent_index: int
    wallet_address: str
    ens_name: str | None = None
    created_date: datetime
