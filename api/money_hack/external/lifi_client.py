from core.requester import Requester
from pydantic import BaseModel


class LiFiToken(BaseModel):
    address: str
    symbol: str
    decimals: int
    chainId: int
    name: str


class LiFiEstimate(BaseModel):
    fromAmount: str
    toAmount: str
    toAmountMin: str
    approvalAddress: str


class LiFiAction(BaseModel):
    fromChainId: int
    toChainId: int
    fromToken: LiFiToken
    toToken: LiFiToken
    fromAmount: str


class LiFiTransactionRequest(BaseModel):
    to: str
    data: str
    value: str
    chainId: int
    gasLimit: str | None = None


class LiFiQuote(BaseModel):
    tool: str
    type: str
    action: LiFiAction
    estimate: LiFiEstimate
    transactionRequest: LiFiTransactionRequest


class LiFiStatusResponse(BaseModel):
    status: str
    substatus: str | None = None
    bridgeName: str | None = None
    sending: dict | None = None
    receiving: dict | None = None


class LiFiClient:
    API_BASE = 'https://li.quest/v1'

    def __init__(self, requester: Requester) -> None:
        self.requester = requester

    async def get_quote(
        self,
        fromChain: int,
        toChain: int,
        fromToken: str,
        toToken: str,
        fromAmount: str,
        fromAddress: str,
        toAddress: str | None = None,
    ) -> LiFiQuote:
        """Get a quote for a cross-chain swap/bridge/deposit via LI.FI."""
        url = f'{self.API_BASE}/quote'
        params = {
            'fromChain': str(fromChain),
            'toChain': str(toChain),
            'fromToken': fromToken,
            'toToken': toToken,
            'fromAmount': fromAmount,
            'fromAddress': fromAddress,
        }
        if toAddress:
            params['toAddress'] = toAddress
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        responseJson = await self.requester.make_request(method='GET', url=f'{url}?{query}')
        return LiFiQuote.model_validate(responseJson)

    async def get_status(
        self,
        bridge: str,
        fromChain: int,
        toChain: int,
        txHash: str,
    ) -> LiFiStatusResponse:
        """Check the status of a cross-chain transfer."""
        url = f'{self.API_BASE}/status'
        params = {
            'bridge': bridge,
            'fromChain': str(fromChain),
            'toChain': str(toChain),
            'txHash': txHash,
        }
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        responseJson = await self.requester.make_request(method='GET', url=f'{url}?{query}')
        return LiFiStatusResponse.model_validate(responseJson)
