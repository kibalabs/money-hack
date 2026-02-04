import base64
import hashlib
import json
import secrets
import time
import typing
import uuid
from urllib.parse import urlparse

import jwt
import rlp  # type: ignore[import-untyped]
from core.exceptions import KibaException
from core.http.rest_method import RestMethod
from core.requester import Requester
from core.util import chain_util
from core.util.typing_util import Json
from core.util.typing_util import JsonObject
from cryptography.hazmat.primitives import asymmetric
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from eth_utils import encode_hex
from eth_utils import to_bytes
from pydantic import BaseModel
from web3.types import TxParams

from money_hack import constants

IMPORT_ACCOUNT_PUBLIC_RSA_KEY = """-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA2Fxydgm/ryYk0IexQIuL
9DKyiIk2WmS36AZ83a9Z0QX53qdveg08b05g1Qr+o+COoYOT/FDi8anRGAs7rIyS
uigrjHR6VrmFjnGrrTr3MINwC9cYQFHwET8YVGRq+BB3iFTB1kIb9XJ/vT2sk1xP
hJ6JihEwSl4DgbeVjqw59wYqrNg355oa8EdFqkmfGU2tpbM56F8iv1F+shwkGo3y
GhW/UOQ5OLauXvsqo8ranwsK+lqFblLEMlNtn1VSJeO2vMxryeKFrY2ob8VqGchC
ftPJiLWs2Du6juw4C1rOWwSMlXzZ6cNMHkxdTcEHMr3C2TEHgzjZY41whMwNTB8q
/pxXnIbH77caaviRs4R/POe8cSsznalXj85LULvFWOIHp0w+jEYSii9Rp9XtHWAH
nrK/O/SVDtT1ohp2F+Zg1mojTgKfLOyGdOUXTi95naDTuG770rSjHdL80tJBz1Fd
+1pzGTGXGHLZQLX5YZm5iuy2cebWfF09VjIoCIlDB2++tr4M+O0Z1X1ZE0J5Ackq
rOluAFalaKynyH3KMyRg+NuLmibu5OmcMjCLK3D4X1YLiN2OK8/bbpEL8JYroDwb
EXIUW5mGS06YxfSUsxHzL9Tj00+GMm/Gvl0+4/+Vn8IXVHjQOSPNEy3EnqCiH/OW
8v0IMC32CeGrX7mGbU+MzlsCAwEAAQ==
-----END PUBLIC KEY-----"""


class ClientAssetBalance(BaseModel):
    assetAddress: str
    balance: int


def sort_json_object(obj: typing.Any) -> typing.Any:  # type: ignore[explicit-any]
    if not obj or not isinstance(obj, dict | list):
        return obj
    if isinstance(obj, list):
        return [sort_json_object(item) for item in obj]
    return {key: sort_json_object(obj[key]) for key in sorted(obj.keys())}


class CoinbaseCdpClient:
    def __init__(
        self,
        requester: Requester,
        walletSecret: str,
        apiKeyName: str,
        apiKeyPrivateKey: str,
    ) -> None:
        self.requester = requester
        self.walletSecret = walletSecret
        self.apiKeyName = apiKeyName
        self.apiKeyPrivateKey = apiKeyPrivateKey

    def _parse_private_key(self, keyString: str) -> PrivateKeyTypes:
        keyData = keyString.encode()
        try:
            return serialization.load_pem_private_key(keyData, password=None)
        except Exception as exception:
            decodedKey = base64.b64decode(keyString)
            if len(decodedKey) == 32:  # noqa: PLR2004
                return asymmetric.ed25519.Ed25519PrivateKey.from_private_bytes(decodedKey)
            if len(decodedKey) == 64:  # noqa: PLR2004
                return asymmetric.ed25519.Ed25519PrivateKey.from_private_bytes(decodedKey[:32])
            raise KibaException('Ed25519 private key must be 32 or 64 bytes after base64 decoding') from exception

    def _signable_uri(self, url: str, method: str) -> str:
        parsedUrl = urlparse(url)
        return f'{method} {parsedUrl.netloc}{parsedUrl.path}'

    def _build_api_jwt(self, url: str, method: str) -> str:
        now = int(time.time())
        privateKey = self._parse_private_key(keyString=self.apiKeyPrivateKey)
        if isinstance(privateKey, asymmetric.ec.EllipticCurvePrivateKey):
            alg = 'ES256'
        elif isinstance(privateKey, asymmetric.ed25519.Ed25519PrivateKey):
            alg = 'EdDSA'
        else:
            raise KibaException('Unsupported key type')
        header = {
            'alg': alg,
            'kid': self.apiKeyName,
            'typ': 'JWT',
            'nonce': secrets.token_hex(),
        }
        claims = {
            'sub': self.apiKeyName,
            'iss': 'cdp',
            'aud': ['cdp_service'],
            'nbf': now,
            'exp': now + 60,
            'uris': [self._signable_uri(url=url, method=method)],
        }
        return jwt.encode(claims, privateKey, algorithm=alg, headers=header)

    def _build_wallet_jwt(self, url: str, method: str, body: Json | None) -> str:
        now = int(time.time())
        uri = self._signable_uri(url=url, method=method)
        payload = {'iat': now, 'nbf': now, 'jti': str(uuid.uuid4()), 'uris': [uri]}
        if body:
            if not isinstance(body, dict):
                raise KibaException('Body must be a dictionary')
            sortedBody = sort_json_object(body)
            bodyString = json.dumps(sortedBody, separators=(',', ':'), sort_keys=True)
            bodyHash = hashlib.sha256(bodyString.encode('utf-8')).hexdigest()
            payload['reqHash'] = bodyHash
        derKeyBytes = serialization.load_der_private_key(data=base64.b64decode(self.walletSecret), password=None)
        token = jwt.encode(
            payload=payload,
            key=typing.cast(asymmetric.ec.EllipticCurvePrivateKey, derKeyBytes),
            algorithm='ES256',
            headers={'typ': 'JWT'},
        )
        return token

    def _build_api_headers(self, url: str, method: str) -> dict[str, str]:
        apiAuthToken = self._build_api_jwt(url=url, method=method)
        headers = {
            'Authorization': f'Bearer {apiAuthToken}',
            'Content-Type': 'application/json',
        }
        return headers

    def _build_wallet_api_headers(self, url: str, method: str, body: Json | None = None) -> dict[str, str]:
        walletAuthToken = self._build_wallet_jwt(url=url, method=method, body=body)
        apiHeaders = self._build_api_headers(url=url, method=method)
        headers = {
            **apiHeaders,
            'X-Wallet-Auth': walletAuthToken,
        }
        return headers

    async def create_eoa(self, name: str) -> str:
        method = RestMethod.POST
        url = 'https://api.cdp.coinbase.com/platform/v2/evm/accounts'
        payload = {
            'name': name,
        }
        headers = self._build_wallet_api_headers(url=url, method=method, body=payload)
        response = await self.requester.make_request(method=method, url=url, dataDict=payload, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['address'])

    async def get_eoa_by_name(self, name: str) -> str:
        method = RestMethod.GET
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/by-name/{name}'
        headers = self._build_api_headers(url=url, method=method)
        response = await self.requester.make_request(method=method, url=url, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['address'])

    async def import_eoa(self, privateKey: str, name: str) -> None:
        method = RestMethod.POST
        url = 'https://api.cdp.coinbase.com/platform/v2/evm/accounts/import'
        privateKeyHex = privateKey.removeprefix('0x')
        privateKeyBytes = bytes.fromhex(privateKeyHex)
        publicKey = typing.cast(asymmetric.rsa.RSAPublicKey, serialization.load_pem_public_key(data=IMPORT_ACCOUNT_PUBLIC_RSA_KEY.encode()))
        encryptedPrivateKey = publicKey.encrypt(
            plaintext=privateKeyBytes,
            padding=asymmetric.padding.OAEP(
                mgf=asymmetric.padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        encryptedPrivateKeyStr = base64.b64encode(encryptedPrivateKey).decode('utf-8')
        dataDict = {
            'encryptedPrivateKey': encryptedPrivateKeyStr,
            'name': name,
        }
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)

    async def sign_hash(self, walletAddress: str, messageHash: str) -> str:
        method = RestMethod.POST
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/{walletAddress}/sign'
        dataDict = {'hash': messageHash}
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['signature'])

    async def sign_transaction(self, walletAddress: str, transactionDict: TxParams) -> str:
        method = RestMethod.POST
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/accounts/{walletAddress}/sign/transaction'
        transactionParts = [
            int(transactionDict['chainId'], 16) if isinstance(transactionDict['chainId'], str) else transactionDict['chainId'],  # type: ignore[unreachable]
            int(transactionDict['nonce'], 16) if isinstance(transactionDict['nonce'], str) else transactionDict['nonce'],  # type: ignore[unreachable]
            int(transactionDict['maxPriorityFeePerGas'], 16) if isinstance(transactionDict['maxPriorityFeePerGas'], str) else transactionDict['maxPriorityFeePerGas'],
            int(transactionDict['maxFeePerGas'], 16) if isinstance(transactionDict['maxFeePerGas'], str) else transactionDict['maxFeePerGas'],
            int(transactionDict['gas'], 16) if isinstance(transactionDict['gas'], str) else transactionDict['gas'],  # type: ignore[unreachable]
            to_bytes(hexstr=transactionDict['to']),
            int(transactionDict['value'], 16) if isinstance(transactionDict['value'], str) else transactionDict['value'],  # type: ignore[unreachable]
            to_bytes(hexstr=transactionDict['data']),
            transactionDict.get('accessList', []),
        ]
        transactionStringBytes = b'\x02' + rlp.encode(transactionParts)
        transactionString = encode_hex(transactionStringBytes)
        dataDict = {'transaction': transactionString}
        headers = self._build_wallet_api_headers(url=url, method=method, body=dataDict)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['signedTransaction'])

    async def get_wallet_asset_balances(self, chainId: int, walletAddress: str) -> list[ClientAssetBalance]:
        if chainId == constants.ETH_CHAIN_ID:
            network = 'ethereum'
        elif chainId == constants.BASE_CHAIN_ID:
            network = 'base'
        else:
            raise KibaException(f'Unsupported chainId: {chainId}')
        allBalances: list[ClientAssetBalance] = []
        pageToken: str | None = None
        method = RestMethod.GET
        url = f'https://api.cdp.coinbase.com/platform/v2/evm/token-balances/{network}/{walletAddress}'
        dataDict: JsonObject = {'pageSize': 50}
        while True:
            if pageToken:
                dataDict['pageToken'] = pageToken
            headers = self._build_api_headers(url=url, method=method)
            response = await self.requester.make_request(method=method, url=url, headers=headers, dataDict=dataDict)
            responseDict = response.json()
            allBalances.extend(
                [
                    ClientAssetBalance(
                        assetAddress=chain_util.normalize_address(balance['token']['contractAddress']),
                        balance=int(balance['amount']['amount']),
                    )
                    for balance in responseDict['balances']
                ]
            )
            pageToken = responseDict.get('nextPageToken')
            if not pageToken:
                break
        return allBalances

    async def generate_onramp_buy_url(self, walletAddress: str, clientIp: str, assets: list[str] | None = None, networks: list[str] | None = None) -> str:
        sessionToken = await self._generate_onramp_session_token(walletAddress=walletAddress, clientIp=clientIp, assets=assets, networks=networks)
        baseUrl = 'https://pay.coinbase.com/buy/select-asset'
        params = [
            f'sessionToken={sessionToken}',
            'defaultNetwork=base',
            'defaultAsset=USDC',
            'fiatCurrency=USD',
            'defaultExperience=buy',
            'presetFiatAmount=1000',
        ]
        return f'{baseUrl}?{"&".join(params)}'

    async def _generate_onramp_session_token(self, walletAddress: str, clientIp: str, assets: list[str] | None = None, networks: list[str] | None = None) -> str:
        method = RestMethod.POST
        url = 'https://api.developer.coinbase.com/onramp/v1/token'
        if assets is None:
            assets = ['USDC']
        if networks is None:
            networks = ['base']
        dataDict: JsonObject = {'addresses': [{'address': walletAddress, 'blockchains': networks}], 'assets': assets, 'clientIp': clientIp}
        headers = self._build_api_headers(url=url, method=method)
        response = await self.requester.make_request(method=method, url=url, dataDict=dataDict, headers=headers)
        responseDict = response.json()
        return typing.cast(str, responseDict['token'])
