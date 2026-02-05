from pydantic import BaseModel
from pydantic import ConfigDict

from money_hack.api import v1_resources as resources


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
    agent_name: str
    agent_emoji: str


class CreatePositionResponse(BaseModel):
    position: resources.Position
    agent: resources.Agent


class WithdrawRequest(BaseModel):
    amount: str


class WithdrawResponse(BaseModel):
    transactions: list[resources.TransactionCall]
    withdraw_amount: str
    vault_address: str


class ClosePositionRequest(BaseModel):
    pass


class ClosePositionResponse(BaseModel):
    transactions: list[resources.TransactionCall]
    collateral_amount: str
    repay_amount: str
    vault_withdraw_amount: str
    morpho_address: str
    vault_address: str


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
    bot_username: str


class TelegramSecretVerifyRequest(BaseModel):
    telegram_secret: str


class TelegramSecretVerifyResponse(BaseModel):
    user_config: resources.UserConfig


class TelegramWebhookRequest(BaseModel):
    model_config = ConfigDict(extra='allow')


class TelegramWebhookResponse(BaseModel):
    pass


class DisconnectTelegramRequest(BaseModel):
    pass


class DisconnectTelegramResponse(BaseModel):
    user_config: resources.UserConfig


class CheckEnsNameRequest(BaseModel):
    label: str


class CheckEnsNameResponse(BaseModel):
    label: str
    full_name: str
    available: bool
    error: str | None = None


class GetEnsConfigTransactionsRequest(BaseModel):
    collateral: str | None = None
    target_ltv: int | None = None
    max_ltv: int | None = None
    min_ltv: int | None = None
    auto_rebalance: bool = True
    risk_tolerance: str = 'medium'
    description: str | None = None


class GetEnsConfigTransactionsResponse(BaseModel):
    transactions: list[resources.TransactionCall]
    ens_name: str


class CreateAgentRequest(BaseModel):
    name: str
    emoji: str


class CreateAgentResponse(BaseModel):
    agent: resources.Agent


class DeployAgentRequest(BaseModel):
    collateral_asset_address: str
    collateral_amount: str
    target_ltv: float


class DeployAgentResponse(BaseModel):
    position: resources.Position
    transaction_hash: str | None = None


class GetAgentRequest(BaseModel):
    pass


class GetAgentResponse(BaseModel):
    agent: resources.Agent | None


class SendChatMessageRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class SendChatMessageResponse(BaseModel):
    messages: list[resources.ChatMessage]
    conversation_id: str


class GetChatHistoryRequest(BaseModel):
    conversation_id: str | None = None
    limit: int = 50


class GetChatHistoryResponse(BaseModel):
    messages: list[resources.ChatMessage]
    conversation_id: str


class GetAgentThoughtsRequest(BaseModel):
    limit: int = 100
    hours_back: int = 24


class GetAgentThoughtsResponse(BaseModel):
    actions: list[resources.AgentActionResource]
