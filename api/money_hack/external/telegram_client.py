import hashlib
import hmac
import uuid

import telegramify_markdown  # type: ignore[import-untyped]
from core import logging
from core.exceptions import BadRequestException
from core.requester import Requester
from core.util import chain_util
from pydantic import BaseModel


class TelegramResponse(BaseModel):
    ok: bool
    result: dict[str, object] | bool | None = None
    error_code: int | None = None
    description: str | None = None


class TelegramBotWebhookInfo(BaseModel):
    url: str | None
    ipAddress: str | None
    hasCustomCertificate: bool
    pendingUpdateCount: int
    maxConnections: int
    allowedUpdates: list[str]


class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TelegramLoginResult(BaseModel):
    walletAddress: str
    telegramUsername: str
    chatId: str


class TelegramClient:
    def __init__(self, requester: Requester, botToken: str, appUrl: str, redirectUri: str, origin: str) -> None:
        self.requester = requester
        self.botToken = botToken
        self.appUrl = appUrl
        self.redirectUri = redirectUri
        self.origin = origin
        self.baseUrl = 'https://api.telegram.org'
        self.botApiUrl = f'{self.baseUrl}/bot{botToken}'
        self.botUsername: str = ''
        self.secretCodeChatIdUsernameCache: dict[str, tuple[str, str]] = {}

    async def send_message(self, chatId: int | str, text: str) -> None:
        url = f'{self.botApiUrl}/sendMessage'
        logging.info(f'[TELEGRAM] Original text: {text}')
        text = telegramify_markdown.markdownify(text)
        logging.info(f'[TELEGRAM] After markdownify: {text}')
        data = {
            'chat_id': chatId,
            'text': text,
            'parse_mode': 'MarkdownV2',
        }
        response = await self.requester.post_json(url=url, dataDict=data, timeout=30)
        responseDict = response.json()
        logging.info(f'[TELEGRAM] Response: {responseDict}')
        if not responseDict.get('ok'):
            raise BadRequestException(f'Failed to send message: {responseDict}')

    async def send_message_html(self, chatId: int | str, text: str) -> None:
        url = f'{self.botApiUrl}/sendMessage'
        data = {
            'chat_id': chatId,
            'text': text,
            'parse_mode': 'HTML',
        }
        response = await self.requester.post_json(url=url, dataDict=data, timeout=30)
        responseDict = response.json()
        if not responseDict.get('ok'):
            raise BadRequestException(f'Failed to send message: {responseDict}')

    async def get_bot_username(self) -> str:
        url = f'{self.botApiUrl}/getMe'
        try:
            response = await self.requester.get(url=url, timeout=30)
            responseData: TelegramResponse = TelegramResponse(**response.json())
        except (ValueError, KeyError, AttributeError) as e:
            logging.exception(f'[TELEGRAM] Error getting bot info: {e}')
            raise BadRequestException(f'Failed to get bot info: {e}')
        if not responseData.ok:
            raise BadRequestException(f'Failed to get bot info: {responseData.description}')
        if responseData.result is None:
            raise BadRequestException('No bot info in response')
        botUsername = str(responseData.result.get('username', ''))
        if not botUsername:
            raise BadRequestException('Bot username not found in response')
        return f'@{botUsername}'

    async def send_login_message(self, chatId: str, senderUsername: str) -> None:
        secretCode = str(uuid.uuid4())
        self.secretCodeChatIdUsernameCache[secretCode] = (chatId, senderUsername)
        text = f'Welcome! Please connect your Telegram account through the [BorrowBot app]({self.appUrl}/account?telegramSecret={secretCode}) to link your wallet and start receiving notifications.'
        await self.send_message(chatId=chatId, text=text)

    async def verify_secret_code(self, walletAddress: str, secretCode: str) -> TelegramLoginResult:
        chatId, senderUsername = self.secretCodeChatIdUsernameCache.get(secretCode, (None, None))
        if not chatId or not senderUsername:
            raise BadRequestException('INVALID_SECRET_CODE')
        del self.secretCodeChatIdUsernameCache[secretCode]
        return TelegramLoginResult(walletAddress=walletAddress, telegramUsername=senderUsername, chatId=chatId)

    async def get_bot_webhook_info(self) -> TelegramBotWebhookInfo:
        url = f'{self.botApiUrl}/getWebhookInfo'
        response = await self.requester.make_request(method='GET', url=url, timeout=30)
        responseDict = response.json()
        return TelegramBotWebhookInfo(
            url=responseDict['result'].get('url'),
            hasCustomCertificate=responseDict['result'].get('has_custom_certificate', False),
            pendingUpdateCount=responseDict['result'].get('pending_update_count', 0),
            maxConnections=responseDict['result'].get('max_connections', 40),
            ipAddress=responseDict['result'].get('ip_address'),
            allowedUpdates=responseDict['result'].get('allowed_updates', []),
        )

    async def set_bot_webhook(self, webhookUrl: str) -> None:
        url = f'{self.botApiUrl}/setWebhook'
        payload = {
            'url': webhookUrl,
            'allowed_updates': ['message'],
        }
        response = await self.requester.post_json(url=url, dataDict=payload, timeout=30)
        responseDict = response.json()
        if not responseDict.get('ok'):
            raise BadRequestException(f'Failed to set webhook: {responseDict}')

    def verify_telegram_auth(self, authData: TelegramAuthData | dict[str, object]) -> bool:
        authDict = authData.model_dump(exclude={'hash'}) if isinstance(authData, TelegramAuthData) else {k: v for k, v in authData.items() if k != 'hash'}
        dataCheckString = '\n'.join([f'{key}={value}' for key, value in sorted(authDict.items())])
        secret = hashlib.sha256(self.botToken.encode()).digest()
        computedHash = hmac.new(secret, dataCheckString.encode(), hashlib.sha256).hexdigest()
        providedHash = authData.hash if isinstance(authData, TelegramAuthData) else authData.get('hash', '')
        return computedHash == providedHash

    async def link_wallet_to_telegram(self, walletAddress: str, chatId: int | str) -> bool:
        walletAddress = chain_util.normalize_address(walletAddress)
        logging.info(f'[TELEGRAM] Linking wallet {walletAddress} to chat_id {chatId}')
        return True

    async def send_position_opened_notification(self, chatId: str, agentName: str, agentEmoji: str, collateralSymbol: str, collateralAmount: str, borrowAmount: str, ltv: float) -> bool:
        text = (
            f'{agentEmoji} *Position Opened*\n\n'
            f'Your agent *{agentName}* has opened a new position:\n\n'
            f'• Collateral: {collateralAmount} {collateralSymbol}\n'
            f'• Borrowed: ${borrowAmount} USDC\n'
            f'• LTV: {ltv:.1%}\n\n'
            f'Your agent will now automatically manage this position to maximize yield while maintaining a healthy LTV\\.'
        )
        return await self.send_message(chatId=chatId, text=text)

    async def send_ltv_adjustment_notification(self, chatId: str, agentName: str, agentEmoji: str, actionType: str, amount: str, oldLtv: float, newLtv: float) -> bool:
        actionText = 'repaid debt' if actionType == 'auto_repay' else 'borrowed more'
        text = f'{agentEmoji} *LTV Adjustment*\n\nYour agent *{agentName}* has {actionText}:\n\n• Amount: ${amount} USDC\n• Previous LTV: {oldLtv:.1%}\n• New LTV: {newLtv:.1%}\n\nThis adjustment helps maintain your target LTV and optimize yield\\.'
        return await self.send_message(chatId=chatId, text=text)

    async def send_critical_ltv_warning(self, chatId: str, agentName: str, agentEmoji: str, currentLtv: float, maxLtv: float) -> bool:
        text = (
            f'⚠️ *Critical LTV Warning*\n\n'
            f'Your agent *{agentName}* {agentEmoji} has an LTV approaching liquidation risk:\n\n'
            f'• Current LTV: {currentLtv:.1%}\n'
            f'• Max LTV: {maxLtv:.1%}\n\n'
            f'Consider adding more collateral or closing your position to avoid liquidation\\.'
        )
        return await self.send_message(chatId=chatId, text=text)

    async def send_position_closed_notification(self, chatId: str, agentName: str, agentEmoji: str, collateralReturned: str, collateralSymbol: str, totalYieldEarned: str) -> bool:
        text = f'{agentEmoji} *Position Closed*\n\nYour agent *{agentName}* has closed its position:\n\n• Collateral Returned: {collateralReturned} {collateralSymbol}\n• Total Yield Earned: ${totalYieldEarned} USDC\n\nThank you for using BorrowBot\\!'
        return await self.send_message(chatId=chatId, text=text)
