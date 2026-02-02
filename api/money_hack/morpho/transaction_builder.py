from typing import TYPE_CHECKING

from core import logging
from core.util import chain_util
from web3 import Web3

from money_hack.api.v1_resources import TransactionCall
from money_hack.morpho import morpho_abis

if TYPE_CHECKING:
    from money_hack.morpho.morpho_client import MorphoMarket

MORPHO_BLUE_ADDRESS = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb'

w3 = Web3()


def encode_approve(spender: str, amount: int) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC20_ABI)
    fn = contract.functions.approve(spender, amount)
    encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_supply_collateral(
    loan_token: str,
    collateral_token: str,
    oracle: str,
    irm: str,
    lltv: int,
    assets: int,
    on_behalf: str,
) -> str:
    market_params = (
        Web3.to_checksum_address(loan_token),
        Web3.to_checksum_address(collateral_token),
        Web3.to_checksum_address(oracle),
        Web3.to_checksum_address(irm),
        lltv,
    )
    contract = w3.eth.contract(abi=morpho_abis.MORPHO_BLUE_ABI)
    fn = contract.functions.supplyCollateral(market_params, assets, Web3.to_checksum_address(on_behalf), b'')
    encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_borrow(
    loan_token: str,
    collateral_token: str,
    oracle: str,
    irm: str,
    lltv: int,
    assets: int,
    on_behalf: str,
    receiver: str,
) -> str:
    market_params = (
        Web3.to_checksum_address(loan_token),
        Web3.to_checksum_address(collateral_token),
        Web3.to_checksum_address(oracle),
        Web3.to_checksum_address(irm),
        lltv,
    )
    contract = w3.eth.contract(abi=morpho_abis.MORPHO_BLUE_ABI)
    fn = contract.functions.borrow(
        market_params,
        assets,
        0,
        Web3.to_checksum_address(on_behalf),
        Web3.to_checksum_address(receiver),
    )
    encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_vault_deposit(assets: int, receiver: str) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC4626_VAULT_ABI)
    fn = contract.functions.deposit(assets, Web3.to_checksum_address(receiver))
    encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


class TransactionBuilder:
    def __init__(self, chainId: int, usdcAddress: str, yoVaultAddress: str) -> None:
        self.chainId = chainId
        self.usdcAddress = chain_util.normalize_address(usdcAddress)
        self.yoVaultAddress = chain_util.normalize_address(yoVaultAddress)
        self.morphoAddress = chain_util.normalize_address(MORPHO_BLUE_ADDRESS)

    def build_position_transactions_from_market(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        borrow_amount: int,
        market: 'MorphoMarket',
    ) -> list[TransactionCall]:
        return self.build_position_transactions(
            user_address=user_address,
            collateral_address=collateral_address,
            collateral_amount=collateral_amount,
            borrow_amount=borrow_amount,
            loan_token=market.loan_address,
            oracle=market.oracle_address,
            irm=market.irm_address,
            lltv=market.lltv_raw,
            needs_collateral_approval=True,
            needs_usdc_approval=True,
        )

    def build_position_transactions(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        borrow_amount: int,
        loan_token: str,
        oracle: str,
        irm: str,
        lltv: int,
        needs_collateral_approval: bool,
        needs_usdc_approval: bool,
    ) -> list[TransactionCall]:
        user = chain_util.normalize_address(user_address)
        collateral = chain_util.normalize_address(collateral_address)
        transactions: list[TransactionCall] = []

        # 1. Approve collateral to Morpho (if needed)
        if needs_collateral_approval:
            approve_calldata = encode_approve(self.morphoAddress, collateral_amount)
            transactions.append(TransactionCall(to=collateral, data=approve_calldata))
            logging.info(f'Added collateral approval tx: {collateral} -> Morpho for {collateral_amount}')

        # 2. Supply collateral to Morpho
        supply_calldata = encode_supply_collateral(
            loan_token=loan_token,
            collateral_token=collateral,
            oracle=oracle,
            irm=irm,
            lltv=lltv,
            assets=collateral_amount,
            on_behalf=user,
        )
        transactions.append(TransactionCall(to=self.morphoAddress, data=supply_calldata))
        logging.info(f'Added supply collateral tx: {collateral_amount} to Morpho')

        # 3. Borrow USDC from Morpho
        borrow_calldata = encode_borrow(
            loan_token=loan_token,
            collateral_token=collateral,
            oracle=oracle,
            irm=irm,
            lltv=lltv,
            assets=borrow_amount,
            on_behalf=user,
            receiver=user,
        )
        transactions.append(TransactionCall(to=self.morphoAddress, data=borrow_calldata))
        logging.info(f'Added borrow tx: {borrow_amount} USDC from Morpho')

        # 4. Approve USDC to Yo vault (if needed)
        if needs_usdc_approval:
            usdc_approve_calldata = encode_approve(self.yoVaultAddress, borrow_amount)
            transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
            logging.info(f'Added USDC approval tx: USDC -> Yo vault for {borrow_amount}')

        # 5. Deposit USDC to Yo vault
        deposit_calldata = encode_vault_deposit(borrow_amount, user)
        transactions.append(TransactionCall(to=self.yoVaultAddress, data=deposit_calldata))
        logging.info(f'Added vault deposit tx: {borrow_amount} USDC to Yo vault')

        return transactions
