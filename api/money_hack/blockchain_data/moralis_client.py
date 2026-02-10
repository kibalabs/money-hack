import datetime

from core.caching.cache import Cache
from core.exceptions import InternalServerErrorException
from core.requester import Requester
from core.util import chain_util
from core.util import date_util
from core.util.typing_util import JsonBaseType
from core.util.typing_util import JsonObject

from money_hack import util
from money_hack.blockchain_data.blockchain_data_client import BlockchainDataClient
from money_hack.blockchain_data.blockchain_data_client import ClientAsset
from money_hack.blockchain_data.blockchain_data_client import ClientAssetBalance
from money_hack.blockchain_data.blockchain_data_client import ClientAssetPrice
from money_hack.blockchain_data.blockchain_data_client import ClientWalletErc20Transfer


class MoralisClient(BlockchainDataClient):
    def __init__(self, requester: Requester, apiKey: str, cache: Cache | None = None) -> None:
        self.requester = requester
        self.apiKey = apiKey
        self.cache = cache

    async def get_asset(self, chainId: int, assetAddress: str) -> ClientAsset:
        assetAddress = chain_util.normalize_address(value=assetAddress)
        dataDict: JsonObject = {
            'chain': hex(chainId),
            'addresses[0]': assetAddress,
        }
        url = 'https://deep-index.moralis.io/api/v2.2/erc20/metadata'
        headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
        response = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
        responseData = response.json()
        assetData = responseData[0]
        return ClientAsset(
            address=chain_util.normalize_address(value=assetData['address']),
            decimals=int(assetData['decimals']),
            name=assetData['name'],
            symbol=assetData['symbol'],
            logoUri=assetData['logo'],
            totalSupply=int(assetData['total_supply'] or 0),
            isSpam=bool(assetData.get('possible_spam', False)),
        )

    async def get_asset_current_price(self, chainId: int, assetAddress: str) -> ClientAssetPrice:
        assetAddress = chain_util.normalize_address(value=assetAddress)
        dataDict: JsonObject = {
            'chain': hex(chainId),
            # NOTE(krishan711): exclude things with minimal liqudity
            'min_pair_side_liquidity_usd': 10_000,
        }
        url = f'https://deep-index.moralis.io/api/v2.2/erc20/{assetAddress}/price'
        headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
        priceResponse = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
        priceResponseData = priceResponse.json()
        assetPrice = ClientAssetPrice(
            # price=float(priceResponseData['nativePrice']['value']) / (10 ** int(priceResponseData['nativePrice']['decimals'])),
            priceUsd=float(priceResponseData['usdPrice']),
        )
        return assetPrice

    async def get_block_number_at_date_start(self, chainId: int, date: datetime.date) -> int:
        if date >= date_util.datetime_from_now(days=1).date():
            raise InternalServerErrorException('Cannot get block number for later than today')
        cacheKey = f'moralis-block-number-{chainId}-{date}'
        blockResponseData = await util.get_json_from_optional_cache(cache=self.cache, key=cacheKey)
        if blockResponseData is None:
            dataDict: JsonObject = {
                'chain': hex(chainId),
                'date': date_util.datetime_to_string(dt=date_util.datetime_from_date(date=date), dateFormat='%Y-%m-%d'),
            }
            url = 'https://deep-index.moralis.io/api/v2.2/dateToBlock'
            headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
            priceResponse = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
            blockResponseData = priceResponse.json()
            await util.save_json_to_optional_cache(cache=self.cache, key=cacheKey, value=blockResponseData, expirySeconds=(60 * 60 * 24))
        return int(blockResponseData['block'])

    async def get_asset_price_at_block(self, chainId: int, assetAddress: str, blockNumber: int) -> ClientAssetPrice:
        assetAddress = chain_util.normalize_address(value=assetAddress)
        dataDict: dict[str, JsonBaseType] = {
            'chain': hex(chainId),
            'to_block': blockNumber,
        }
        url = f'https://deep-index.moralis.io/api/v2.2/erc20/{assetAddress}/price'
        headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
        priceResponse = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
        priceResponseData = priceResponse.json()
        assetPrice = ClientAssetPrice(priceUsd=float(priceResponseData['usdPrice']))
        return assetPrice

    async def get_asset_historic_price(self, chainId: int, assetAddress: str, date: datetime.date) -> ClientAssetPrice:
        blockNumber = await self.get_block_number_at_date_end(chainId=chainId, date=date)
        return await self.get_asset_price_at_block(chainId=chainId, assetAddress=assetAddress, blockNumber=blockNumber)

    async def get_wallet_asset_balances(self, chainId: int, walletAddress: str) -> list[ClientAssetBalance]:
        walletAddress = chain_util.normalize_address(value=walletAddress)
        dataDict: dict[str, JsonBaseType] = {
            'chain': hex(chainId),
            'exclude_spam': True,
            'exclude_unverified_contracts': True,
        }
        url = f'https://deep-index.moralis.io/api/v2.2/wallets/{walletAddress}/tokens'
        headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
        response = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
        responseData = response.json()
        return [
            ClientAssetBalance(
                assetAddress=chain_util.normalize_address(value=responseDataItem['token_address']),
                balance=int(responseDataItem['balance']),
            )
            for responseDataItem in responseData['result']
        ]

    async def list_wallet_erc20_transfers(self, chainId: int, walletAddress: str, fromBlock: int, toBlock: int) -> list[ClientWalletErc20Transfer]:
        walletAddress = chain_util.normalize_address(value=walletAddress)
        allTransfers = []
        cursor = None
        while True:
            dataDict: dict[str, JsonBaseType] = {
                'chain': hex(chainId),
                'order': 'ASC',
                'limit': 100,
                'from_block': max(0, fromBlock),
                'to_block': toBlock,
            }
            if cursor is not None:
                dataDict['cursor'] = cursor
            url = f'https://deep-index.moralis.io/api/v2.2/wallets/{walletAddress}/history'
            headers = {'X-API-Key': self.apiKey, 'accept': 'application/json'}
            response = await self.requester.get(url=url, headers=headers, dataDict=dataDict, timeout=60)
            responseData = response.json()
            results = responseData.get('result', [])
            for result in results:
                blockNumber = int(result['block_number'])
                transactionHash = result['hash']
                allTransfers.extend(
                    [
                        ClientWalletErc20Transfer(
                            blockNumber=blockNumber,
                            transactionHash=transactionHash,
                            fromAddress=chain_util.normalize_address(transfer['from_address']),
                            toAddress=chain_util.normalize_address(transfer['to_address']),
                            assetAddress=chain_util.normalize_address(transfer['address']),
                            assetAmount=int(transfer['value']),
                            logIndex=int(transfer.get('log_index')) if transfer.get('log_index') is not None else None,
                        )
                        for transfer in result.get('erc20_transfers', [])
                    ]
                )
            cursor = responseData.get('cursor')
            if cursor is None or len(results) == 0:
                break
        return allTransfers
