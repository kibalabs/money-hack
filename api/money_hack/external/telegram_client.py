import hashlib
import hmac
import secrets

from core import logging
from core.requester import Requester
from core.util import chain_util
from pydantic import BaseModel


class TelegramResponse(BaseModel):
    ok: bool
    result: dict[str, object] | None = None
    error_code: int | None = None
    description: str | None = None


class TelegramWebhookInfo(BaseModel):
    url: str
    has_custom_certificate: bool
    pending_update_count: int


class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


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

    async def send_message(self, chatId: int | str, text: str, parseMode: str = 'MarkdownV2') -> bool:
        url = f'{self.botApiUrl}/sendMessage'
        dataDict: dict[str, int | str] = {
            'chat_id': chatId,
            'text': text,
            'parse_mode': parseMode,
        }
        try:
            response = await self.requester.post(url=url, dataDict=dataDict, timeout=30)
            responseData: TelegramResponse = TelegramResponse(**response.json())
        except (ValueError, KeyError, AttributeError) as e:
            logging.exception(f'[TELEGRAM] Error sending message: {e}')
            return False
        if not responseData.ok:
            logging.error(f'[TELEGRAM] Failed to send message: {responseData.description}')
            return False
        return True

    async def get_login_url(self) -> tuple[str, str]:
        url = f'{self.botApiUrl}/getMe'
        try:
            response = await self.requester.get(url=url, timeout=30)
            responseData: TelegramResponse = TelegramResponse(**response.json())
        except (ValueError, KeyError, AttributeError) as e:
            logging.exception(f'[TELEGRAM] Error getting bot info: {e}')
            raise ValueError(f'Failed to get bot info: {e}')
        if not responseData.ok:
            raise ValueError(f'Failed to get bot info: {responseData.description}')
        if responseData.result is None:
            raise ValueError('No bot info in response')
        botUsername = str(responseData.result.get('username', ''))
        if not botUsername:
            raise ValueError('Bot username not found in response')
        secretCode = secrets.token_hex(16)
        return f'https://t.me/{botUsername}?start={secretCode}', secretCode

    async def set_webhook(self, webhookUrl: str) -> bool:
        url = f'{self.botApiUrl}/setWebhook'
        dataDict: dict[str, str] = {'url': webhookUrl}
        try:
            response = await self.requester.post(url=url, dataDict=dataDict, timeout=30)
            responseData: TelegramResponse = TelegramResponse(**response.json())
        except (ValueError, KeyError, AttributeError) as e:
            logging.exception(f'[TELEGRAM] Error setting webhook: {e}')
            return False
        if not responseData.ok:
            logging.error(f'[TELEGRAM] Failed to set webhook: {responseData.description}')
            return False
        logging.info(f'[TELEGRAM] Webhook set to {webhookUrl}')
        return True

    async def get_webhook_info(self) -> TelegramWebhookInfo:
        url = f'{self.botApiUrl}/getWebhookInfo'
        try:
            response = await self.requester.post(url=url, timeout=30)
            responseData: TelegramResponse = TelegramResponse(**response.json())
        except (ValueError, KeyError, AttributeError) as e:
            logging.exception(f'[TELEGRAM] Error getting webhook info: {e}')
            raise ValueError(f'Failed to get webhook info: {e}')
        if not responseData.ok:
            raise ValueError(f'Failed to get webhook info: {responseData.description}')
        if responseData.result is None:
            raise ValueError('No webhook info in response')
        url_str = str(responseData.result.get('url', ''))
        has_cert = bool(responseData.result.get('has_custom_certificate', False))
        pending_count_obj = responseData.result.get('pending_update_count')
        pending_count = int(pending_count_obj) if isinstance(pending_count_obj, (int, str)) else 0
        return TelegramWebhookInfo(url=url_str, has_custom_certificate=has_cert, pending_update_count=pending_count)

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
