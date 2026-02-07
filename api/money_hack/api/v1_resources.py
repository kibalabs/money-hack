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
    wallet_collateral_balance: str
    wallet_collateral_balance_usd: float
    wallet_usdc_balance: str
    wallet_usdc_balance_usd: float


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


class WithdrawPreview(BaseModel):
    withdraw_amount: str
    vault_balance: str
    max_safe_withdraw: str
    current_ltv: float
    estimated_new_ltv: float
    target_ltv: float
    max_ltv: float
    hard_max_ltv: float
    is_warning: bool
    is_blocked: bool
    warning_message: str | None = None


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


class ChatMessage(BaseModel):
    """A chat message in a conversation."""

    message_id: int
    created_date: datetime
    is_user: bool
    content: str


class ChatResponse(BaseModel):
    """Response from a chat message."""

    messages: list[ChatMessage]
    conversation_id: str


class EnsConstitutionResource(BaseModel):
    """ENS constitution and status for an agent."""

    ens_name: str | None = None
    max_ltv: float | None = None
    min_spread: float | None = None
    max_position_usd: float | None = None
    allowed_collateral: str | None = None
    pause: bool = False
    status: str | None = None
    last_action: str | None = None
    last_check: str | None = None


class AgentActionResource(BaseModel):
    """An agent action or thought."""

    action_id: int
    created_date: datetime
    agent_id: str
    action_type: str
    value: str
    details: dict[str, object]
