import asyncio
import datetime
import typing

from core import logging
from core.caching.cache import Cache
from core.exceptions import BadRequestException
from core.exceptions import InternalServerErrorException
from core.exceptions import NotFoundException
from core.requester import Requester
from core.util import chain_util
from core.util import date_util
from core.util.typing_util import JsonObject
from pydantic import BaseModel

from money_hack import constants
from money_hack import util
from money_hack.blockchain_data.blockchain_data_client import BlockchainDataClient
from money_hack.blockchain_data.blockchain_data_client import ClientAsset
from money_hack.blockchain_data.blockchain_data_client import ClientAssetBalance
from money_hack.blockchain_data.blockchain_data_client import ClientAssetPrice
from money_hack.blockchain_data.blockchain_data_client import ClientWalletErc20Transfer
from money_hack.blockchain_data.blockchain_data_client import PriceNotFoundException
from money_hack.blockchain_data.findblock_client import FindBlockClient


class NftOwner(BaseModel):
    ownerAddress: str
    tokenIds: list[int]


class AlchemyClient(BlockchainDataClient):
    def __init__(self, requester: Requester, apiKey: str, cache: Cache, findBlockClient: FindBlockClient) -> None:
        self.requester = requester
        self.apiKey = apiKey
        self.cache = cache
        self.findBlockClient = findBlockClient

    def _get_network_name(self, chainId: int) -> str:
        if chainId == constants.ETH_CHAIN_ID:
            return 'eth-mainnet'
        if chainId == constants.BASE_CHAIN_ID:
            return 'base-mainnet'
        if chainId == constants.SCROLL_CHAIN_ID:
            return 'scroll-mainnet'
        raise InternalServerErrorException(f'ChainId {chainId} not supported')

    def _get_host(self, chainId: int) -> str:
        return f'https://{self._get_network_name(chainId=chainId)}.g.alchemy.com'

    async def _make_v3_method_request(self, chainId: int, apiType: str, apiPath: str, dataDict: JsonObject) -> typing.Any:  # type: ignore[explicit-any]
        host = self._get_host(chainId=chainId)
        url = f'{host}/{apiType}/v3/{self.apiKey}/{apiPath}'
        response = await self.requester.get(url=url, dataDict=dataDict, timeout=60)
        responseData = response.json()
        return responseData

    async def _make_method_request(self, chainId: int, dataDict: JsonObject) -> typing.Any:  # type: ignore[explicit-any]
        host = self._get_host(chainId=chainId)
        url = f'{host}/v2/{self.apiKey}'
        headers = {'accept': 'application/json'}
        response = await self.requester.post_json(url=url, headers=headers, dataDict=dataDict, timeout=60)
        responseData = response.json()
        return responseData['result']

    async def _make_prices_api_request(self, dataDict: JsonObject, path: str) -> typing.Any:  # type: ignore[explicit-any]
        url = f'https://api.g.alchemy.com/prices/v1/{self.apiKey}/{path}'
        headers = {'accept': 'application/json'}
        try:
            response = await self.requester.post_json(url=url, headers=headers, dataDict=dataDict, timeout=60)
        except BadRequestException as exception:
            if 'Token not found:' in str(exception):
                raise NotFoundException(f'Token not found: {exception}')
            raise
        responseData = response.json()
        return responseData

    async def get_asset(self, chainId: int, assetAddress: str) -> ClientAsset:
        if assetAddress == constants.NATIVE_TOKEN_ADDRESS:
            return ClientAsset(
                address=constants.NATIVE_TOKEN_ADDRESS,
                decimals=18,
                name='Ethereum',
                symbol='ETH',
                logoUri='https://cdn.moralis.io/eth/0x.png',
                totalSupply=0,
                isSpam=False,
            )
        responseData = await self._make_method_request(
            chainId=chainId,
            dataDict={
                'id': 1,
                'jsonrpc': '2.0',
                'method': 'alchemy_getTokenMetadata',
                'params': [assetAddress],
            },
        )
        return ClientAsset(
            address=chain_util.normalize_address(value=assetAddress),
            decimals=int(typing.cast(int, responseData['decimals'])),
            name=typing.cast(str, responseData['name']),
            symbol=typing.cast(str, responseData['symbol']),
            logoUri=typing.cast(str | None, responseData['logo']),
            totalSupply=int(typing.cast(int | None, responseData.get('total_supply')) or 0),
            isSpam=False,
        )

    async def get_asset_current_price(self, chainId: int, assetAddress: str) -> ClientAssetPrice:
        responseData = await self._make_prices_api_request(
            path='tokens/by-address',
            dataDict={
                'addresses': [
                    {
                        'network': self._get_network_name(chainId=chainId),
                        'address': assetAddress,
                    }
                ],
            },
        )
        priceData = responseData['data'][0]
        price = next((price for price in priceData['prices'] if price['currency'].lower() == 'usd'), None)
        if price is None:
            raise NotFoundException(f'Price not found for asset {assetAddress} on chain {chainId}')
        assetPrice = ClientAssetPrice(
            priceUsd=float(price['value']),
        )
        return assetPrice

    async def _get_block_timestamp(self, chainId: int, blockNumber: int) -> int:
        cacheKey = f'alchemy-block-timestamp-{chainId}-{blockNumber}'
        cachedTimestamp = await util.get_json_from_optional_cache(cache=self.cache, key=cacheKey)
        if cachedTimestamp is not None:
            return int(cachedTimestamp)
        blockData = await self._make_method_request(
            chainId=chainId,
            dataDict={
                'id': 1,
                'jsonrpc': '2.0',
                'method': 'eth_getBlockByNumber',
                'params': [hex(blockNumber), False],
            },
        )
        timestamp = int(blockData['timestamp'], 16)
        await util.save_json_to_optional_cache(cache=self.cache, key=cacheKey, value=timestamp, expirySeconds=(60 * 60 * 24 * 365))
        return timestamp

    async def get_asset_price_at_block(self, chainId: int, assetAddress: str, blockNumber: int) -> ClientAssetPrice:
        timestamp = await self._get_block_timestamp(chainId=chainId, blockNumber=blockNumber)
        blockDatetime = datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
        responseData = await self._make_prices_api_request(
            path='tokens/historical',
            dataDict={
                'startTime': date_util.datetime_to_string(dt=blockDatetime, dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                'endTime': date_util.datetime_to_string(dt=blockDatetime + datetime.timedelta(hours=1), dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                'interval': '1h',
                'network': self._get_network_name(chainId=chainId),
                'address': assetAddress,
            },
        )
        if not responseData['data']:
            raise PriceNotFoundException(f'No price data found for asset {assetAddress} at block {blockNumber}')
        priceData = responseData['data'][0]
        return ClientAssetPrice(priceUsd=float(priceData['value']))

    async def get_asset_historic_price(self, chainId: int, assetAddress: str, date: datetime.date) -> ClientAssetPrice:
        responseData = await self._make_prices_api_request(
            path='tokens/historical',
            dataDict={
                'startTime': date_util.datetime_to_string(dt=date_util.datetime_from_date(date=date), dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                'endTime': date_util.datetime_to_string(dt=date_util.end_of_day(dt=date_util.datetime_from_date(date=date)), dateFormat='%Y-%m-%dT%H:%M:%SZ'),
                'interval': '1d',
                'network': self._get_network_name(chainId=chainId),
                'address': assetAddress,
            },
        )
        if not responseData.get('data'):
            logging.warning(f'No price data available for asset {assetAddress} on chainId {chainId} for date {date}, returning 0')
            return ClientAssetPrice(priceUsd=0.0)
        priceData = responseData['data'][0]
        assetPrice = ClientAssetPrice(priceUsd=float(priceData['value']))
        return assetPrice

    async def get_wallet_asset_balances(self, chainId: int, walletAddress: str) -> list[ClientAssetBalance]:
        ethResponseData = await self._make_method_request(
            chainId=chainId,
            dataDict={
                'id': 1,
                'jsonrpc': '2.0',
                'method': 'eth_getBalance',
                'params': [walletAddress, 'latest'],
            },
        )
        ethBalance = int(ethResponseData, 16)
        erc20ResponseData = await self._make_method_request(
            chainId=chainId,
            dataDict={
                'id': 1,
                'jsonrpc': '2.0',
                'method': 'alchemy_getTokenBalances',
                'params': [walletAddress, 'erc20'],
            },
        )
        balances = [ClientAssetBalance(assetAddress=constants.NATIVE_TOKEN_ADDRESS, balance=ethBalance)]
        for responseDataItem in erc20ResponseData['tokenBalances']:
            balance = int(responseDataItem['tokenBalance'], 0)
            if balance == 0:
                continue
            balances.append(
                ClientAssetBalance(
                    assetAddress=chain_util.normalize_address(value=responseDataItem['contractAddress']),
                    balance=balance,
                )
            )
        return balances

    async def get_block_number_at_date_start(self, chainId: int, date: datetime.date) -> int:
        return await self.findBlockClient.get_block_number_at_date_start(chainId=chainId, date=date)

    async def list_wallet_erc20_transfers(self, chainId: int, walletAddress: str, fromBlock: int, toBlock: int) -> list[ClientWalletErc20Transfer]:
        walletAddress = chain_util.normalize_address(value=walletAddress)
        allTransferData = []
        baseParams = {
            'fromBlock': hex(fromBlock),
            'toBlock': hex(toBlock),
            # NOTE: 'internal' transfers are only available on Ethereum mainnet
            # For all other chains (Base, etc), only 'external' and 'erc20' are supported
            'category': ['external', 'erc20'],
            'withMetadata': True,
            'excludeZeroValue': False,
            'maxCount': '0x3e8',
        }
        inboundParams = {**baseParams, 'toAddress': walletAddress}
        pageKey = None
        while True:
            if pageKey:
                inboundParams['pageKey'] = pageKey
            responseData = await self._make_method_request(
                chainId=chainId,
                dataDict={
                    'id': 1,
                    'jsonrpc': '2.0',
                    'method': 'alchemy_getAssetTransfers',
                    'params': [typing.cast(JsonObject, inboundParams)],
                },
            )
            transfers = responseData.get('transfers', [])
            allTransferData.extend(transfers)
            pageKey = responseData.get('pageKey')
            if not pageKey:
                break
        outboundParams = {**baseParams, 'fromAddress': walletAddress}
        pageKey = None
        while True:
            if pageKey:
                outboundParams['pageKey'] = pageKey
            responseData = await self._make_method_request(
                chainId=chainId,
                dataDict={
                    'id': 1,
                    'jsonrpc': '2.0',
                    'method': 'alchemy_getAssetTransfers',
                    'params': [typing.cast(JsonObject, outboundParams)],
                },
            )
            transfers = responseData.get('transfers', [])
            allTransferData.extend(transfers)
            pageKey = responseData.get('pageKey')
            if not pageKey:
                break
        allTransfers = []
        for transferData in allTransferData:
            # Native ETH transfers use 'category': 'external' and don't have rawContract
            # ERC20 transfers have 'category': 'erc20' and include rawContract
            category = transferData.get('category')
            if category == 'external':
                # Native ETH transfer - use the standard native token address
                assetAddress = constants.NATIVE_TOKEN_ADDRESS
                rawValue = transferData.get('value', 0)
                assetAmount = int(float(rawValue) * 1e18) if rawValue else 0
            elif category == 'erc20':
                # ERC20 transfer - use rawContract data
                if 'rawContract' not in transferData or not transferData['rawContract'].get('address') or not transferData['rawContract'].get('value'):
                    continue
                assetAddress = chain_util.normalize_address(value=transferData['rawContract']['address'])
                rawValue = transferData['rawContract']['value']
                assetAmount = int(rawValue, 16) if isinstance(rawValue, str) and rawValue.startswith('0x') else int(rawValue or 0)
            else:
                # Skip other categories (shouldn't happen with our filter)
                continue
            blockNumber = transferData['blockNum']
            if isinstance(blockNumber, str):
                blockNumber = int(blockNumber, 16) if blockNumber.startswith('0x') else int(blockNumber)
            transfer = ClientWalletErc20Transfer(
                blockNumber=blockNumber,
                transactionHash=transferData['hash'],
                fromAddress=chain_util.normalize_address(value=transferData['from']),
                # NOTE(krishan711): to isnt filled when creating a contract which i did with krishan711's agent!
                toAddress=chain_util.normalize_address(value=transferData['to'] or chain_util.BURN_ADDRESS),
                assetAddress=assetAddress,
                assetAmount=assetAmount,
                logIndex=transferData.get('logIndex'),
            )
            allTransfers.append(transfer)
        # Detect internal ETH transfers by finding transactions with incoming but no outgoing.
        # These are likely swaps where ETH went out but isn't captured by alchemy_getAssetTransfers
        # because the 'internal' category is only supported on Ethereum mainnet.
        inboundTxHashes = {transfer.transactionHash for transfer in allTransfers if transfer.toAddress == walletAddress}
        outboundTxHashes = {transfer.transactionHash for transfer in allTransfers if transfer.fromAddress == walletAddress}
        suspiciousTxHashes = inboundTxHashes - outboundTxHashes
        logging.info(f'SYNTHETIC_ETH: Found {len(suspiciousTxHashes)} suspicious transactions (incoming but no outgoing)')
        processedTxHashes: set[str] = set()
        for transfer in allTransfers:
            if transfer.transactionHash not in suspiciousTxHashes:
                continue
            if transfer.transactionHash in processedTxHashes:
                continue
            if transfer.toAddress != walletAddress:
                continue
            logging.info(f'SYNTHETIC_ETH: Checking tx {transfer.transactionHash[:16]}... at block {transfer.blockNumber} for ETH balance change')
            balanceBefore, balanceAfter = await asyncio.gather(
                self._make_method_request(
                    chainId=chainId,
                    dataDict={'id': 1, 'jsonrpc': '2.0', 'method': 'eth_getBalance', 'params': [walletAddress, hex(transfer.blockNumber - 1)]},
                ),
                self._make_method_request(
                    chainId=chainId,
                    dataDict={'id': 1, 'jsonrpc': '2.0', 'method': 'eth_getBalance', 'params': [walletAddress, hex(transfer.blockNumber)]},
                ),
            )
            ethChange = int(balanceAfter, 16) - int(balanceBefore, 16)
            logging.info(f'SYNTHETIC_ETH: ETH balance change: {ethChange} wei ({ethChange / 1e18} ETH)')
            if ethChange >= 0:
                # If eth grew we would have captured that transfer somewhere already
                logging.info('SYNTHETIC_ETH: ETH increased or stayed same, skipping')
                continue
            logging.info(f'SYNTHETIC_ETH: Creating synthetic ETH withdrawal for {abs(ethChange)} wei')
            syntheticTransfer = ClientWalletErc20Transfer(
                blockNumber=transfer.blockNumber,
                transactionHash=transfer.transactionHash,
                fromAddress=walletAddress,
                toAddress=chain_util.normalize_address(value='0x0000000000000000000000000000000000000000'),
                assetAddress=constants.NATIVE_TOKEN_ADDRESS,
                assetAmount=abs(ethChange),
                logIndex=None,
            )
            allTransfers.append(syntheticTransfer)
            processedTxHashes.add(transfer.transactionHash)
        return allTransfers

    async def list_nft_owners(self, chainId: int, contractAddress: str, shouldForceRefresh: bool = False) -> list[NftOwner]:
        cacheKey = f'alchemy-nft-owners-{chainId}-{contractAddress}'
        responseData = await util.get_json_from_optional_cache(cache=self.cache, key=cacheKey)
        if shouldForceRefresh or responseData is None:
            responseData = await self._make_v3_method_request(
                chainId=chainId,
                apiType='nft',
                apiPath='getOwnersForContract',
                dataDict={
                    'contractAddress': contractAddress,
                    'withTokenBalances': True,
                },
            )
            await util.save_json_to_optional_cache(cache=self.cache, key=cacheKey, value=responseData, expirySeconds=(60 * 60 * 12))
        return [
            NftOwner(
                ownerAddress=chain_util.normalize_address(value=ownerItem['ownerAddress']),
                tokenIds=list({balance['tokenId'] for balance in ownerItem['tokenBalances']}),
            )
            for ownerItem in responseData['owners']
        ]
