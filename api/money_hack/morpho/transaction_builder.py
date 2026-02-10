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
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_transfer(recipient: str, amount: int) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC20_ABI)
    fn = contract.functions.transfer(recipient, amount)
    encoded = fn._encode_transaction_data()  # noqa: SLF001
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
    encoded = fn._encode_transaction_data()  # noqa: SLF001
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
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_repay(
    loan_token: str,
    collateral_token: str,
    oracle: str,
    irm: str,
    lltv: int,
    assets: int,
    on_behalf: str,
    shares: int = 0,
) -> str:
    market_params = (
        Web3.to_checksum_address(loan_token),
        Web3.to_checksum_address(collateral_token),
        Web3.to_checksum_address(oracle),
        Web3.to_checksum_address(irm),
        lltv,
    )
    contract = w3.eth.contract(abi=morpho_abis.MORPHO_BLUE_ABI)
    fn = contract.functions.repay(market_params, assets, shares, Web3.to_checksum_address(on_behalf), b'')
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_withdraw_collateral(
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
    fn = contract.functions.withdrawCollateral(
        market_params,
        assets,
        Web3.to_checksum_address(on_behalf),
        Web3.to_checksum_address(receiver),
    )
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_vault_deposit(assets: int, receiver: str) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC4626_VAULT_ABI)
    fn = contract.functions.deposit(assets, Web3.to_checksum_address(receiver))
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_vault_withdraw(assets: int, receiver: str, owner: str) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC4626_VAULT_ABI)
    fn = contract.functions.withdraw(assets, Web3.to_checksum_address(receiver), Web3.to_checksum_address(owner))
    encoded = fn._encode_transaction_data()  # noqa: SLF001
    return str(encoded) if isinstance(encoded, (bytes, str)) else encoded


def encode_vault_redeem(shares: int, receiver: str, owner: str) -> str:
    contract = w3.eth.contract(abi=morpho_abis.ERC4626_VAULT_ABI)
    fn = contract.functions.redeem(shares, Web3.to_checksum_address(receiver), Web3.to_checksum_address(owner))
    encoded = fn._encode_transaction_data()  # noqa: SLF001
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

    def build_withdraw_transactions(
        self,
        user_address: str,
        withdraw_shares: int,
    ) -> list[TransactionCall]:
        """Build transactions to withdraw USDC from the vault by redeeming shares (partial withdrawal, keeps position open)."""
        user = chain_util.normalize_address(user_address)
        transactions: list[TransactionCall] = []
        redeem_calldata = encode_vault_redeem(shares=withdraw_shares, receiver=user, owner=user)
        transactions.append(TransactionCall(to=self.yoVaultAddress, data=redeem_calldata))
        logging.info(f'Added vault redeem tx: {withdraw_shares} shares from Yo vault')
        return transactions

    def build_close_position_transactions_from_market(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        repay_amount: int,
        vault_withdraw_amount: int,
        market: 'MorphoMarket',
        needs_usdc_approval: bool,
        vault_shares: int = 0,
        borrow_shares: int = 0,
    ) -> list[TransactionCall]:
        return self.build_close_position_transactions(
            user_address=user_address,
            collateral_address=collateral_address,
            collateral_amount=collateral_amount,
            repay_amount=repay_amount,
            vault_withdraw_amount=vault_withdraw_amount,
            loan_token=market.loan_address,
            oracle=market.oracle_address,
            irm=market.irm_address,
            lltv=market.lltv_raw,
            needs_usdc_approval=needs_usdc_approval,
            vault_shares=vault_shares,
            borrow_shares=borrow_shares,
        )

    def build_close_position_transactions(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        repay_amount: int,
        vault_withdraw_amount: int,
        loan_token: str,
        oracle: str,
        irm: str,
        lltv: int,
        needs_usdc_approval: bool,
        vault_shares: int = 0,
        borrow_shares: int = 0,
    ) -> list[TransactionCall]:
        """Build transactions to fully close a position: redeem from vault, repay debt, withdraw collateral."""
        user = chain_util.normalize_address(user_address)
        collateral = chain_util.normalize_address(collateral_address)
        transactions: list[TransactionCall] = []
        # 1. Redeem all shares from Yo vault (to get funds to repay)
        if vault_shares > 0:
            redeem_calldata = encode_vault_redeem(shares=vault_shares, receiver=user, owner=user)
            transactions.append(TransactionCall(to=self.yoVaultAddress, data=redeem_calldata))
            logging.info(f'Added vault redeem tx: {vault_shares} shares from Yo vault')
        else:
            withdraw_calldata = encode_vault_withdraw(assets=vault_withdraw_amount, receiver=user, owner=user)
            transactions.append(TransactionCall(to=self.yoVaultAddress, data=withdraw_calldata))
            logging.info(f'Added vault withdraw tx: {vault_withdraw_amount} USDC from Yo vault')
        # 2. Approve USDC to Morpho for repayment (if needed)
        if needs_usdc_approval:
            approve_amount = repay_amount * 2  # Approve extra to cover any interest accrual
            usdc_approve_calldata = encode_approve(self.morphoAddress, approve_amount)
            transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
            logging.info(f'Added USDC approval tx: USDC -> Morpho for {approve_amount}')
        # 3. Repay debt to Morpho (use shares for exact repayment when available)
        if borrow_shares > 0:
            repay_calldata = encode_repay(
                loan_token=loan_token,
                collateral_token=collateral,
                oracle=oracle,
                irm=irm,
                lltv=lltv,
                assets=0,
                shares=borrow_shares,
                on_behalf=user,
            )
            transactions.append(TransactionCall(to=self.morphoAddress, data=repay_calldata))
            logging.info(f'Added repay tx: {borrow_shares} borrow shares to Morpho')
        else:
            repay_calldata = encode_repay(
                loan_token=loan_token,
                collateral_token=collateral,
                oracle=oracle,
                irm=irm,
                lltv=lltv,
                assets=repay_amount,
                on_behalf=user,
            )
            transactions.append(TransactionCall(to=self.morphoAddress, data=repay_calldata))
            logging.info(f'Added repay tx: {repay_amount} USDC to Morpho')
        # 4. Withdraw collateral from Morpho
        withdraw_collateral_calldata = encode_withdraw_collateral(
            loan_token=loan_token,
            collateral_token=collateral,
            oracle=oracle,
            irm=irm,
            lltv=lltv,
            assets=collateral_amount,
            on_behalf=user,
            receiver=user,
        )
        transactions.append(TransactionCall(to=self.morphoAddress, data=withdraw_collateral_calldata))
        logging.info(f'Added withdraw collateral tx: {collateral_amount} from Morpho')
        return transactions

    def build_partial_repay_transactions_from_market(
        self,
        user_address: str,
        collateral_address: str,
        repay_amount: int,
        vault_withdraw_amount: int,
        market: 'MorphoMarket',
        needs_usdc_approval: bool,
    ) -> list[TransactionCall]:
        return self.build_partial_repay_transactions(
            user_address=user_address,
            collateral_address=collateral_address,
            repay_amount=repay_amount,
            vault_withdraw_amount=vault_withdraw_amount,
            loan_token=market.loan_address,
            oracle=market.oracle_address,
            irm=market.irm_address,
            lltv=market.lltv_raw,
            needs_usdc_approval=needs_usdc_approval,
        )

    def build_partial_repay_transactions(
        self,
        user_address: str,
        collateral_address: str,
        repay_amount: int,
        vault_withdraw_amount: int,
        loan_token: str,
        oracle: str,
        irm: str,
        lltv: int,
        needs_usdc_approval: bool,
    ) -> list[TransactionCall]:
        """Build transactions for partial repay (auto-repay): withdraw from vault, repay debt (no collateral withdrawal)."""
        user = chain_util.normalize_address(user_address)
        collateral = chain_util.normalize_address(collateral_address)
        transactions: list[TransactionCall] = []
        withdraw_calldata = encode_vault_withdraw(assets=vault_withdraw_amount, receiver=user, owner=user)
        transactions.append(TransactionCall(to=self.yoVaultAddress, data=withdraw_calldata))
        logging.info(f'Added vault withdraw tx: {vault_withdraw_amount} USDC from Yo vault')
        if needs_usdc_approval:
            usdc_approve_calldata = encode_approve(self.morphoAddress, repay_amount)
            transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
            logging.info(f'Added USDC approval tx: USDC -> Morpho for {repay_amount}')
        repay_calldata = encode_repay(
            loan_token=loan_token,
            collateral_token=collateral,
            oracle=oracle,
            irm=irm,
            lltv=lltv,
            assets=repay_amount,
            on_behalf=user,
        )
        transactions.append(TransactionCall(to=self.morphoAddress, data=repay_calldata))
        logging.info(f'Added repay tx: {repay_amount} USDC to Morpho')
        return transactions

    def build_repay_and_withdraw_collateral_transactions_from_market(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        repay_amount: int,
        market: 'MorphoMarket',
        needs_usdc_approval: bool,
        borrow_shares: int = 0,
    ) -> list[TransactionCall]:
        return self.build_repay_and_withdraw_collateral_transactions(
            user_address=user_address,
            collateral_address=collateral_address,
            collateral_amount=collateral_amount,
            repay_amount=repay_amount,
            loan_token=market.loan_address,
            oracle=market.oracle_address,
            irm=market.irm_address,
            lltv=market.lltv_raw,
            needs_usdc_approval=needs_usdc_approval,
            borrow_shares=borrow_shares,
        )

    def build_repay_and_withdraw_collateral_transactions(
        self,
        user_address: str,
        collateral_address: str,
        collateral_amount: int,
        repay_amount: int,
        loan_token: str,
        oracle: str,
        irm: str,
        lltv: int,
        needs_usdc_approval: bool,
        borrow_shares: int = 0,
    ) -> list[TransactionCall]:
        user = chain_util.normalize_address(user_address)
        collateral = chain_util.normalize_address(collateral_address)
        transactions: list[TransactionCall] = []
        if needs_usdc_approval:
            approve_amount = repay_amount * 2
            usdc_approve_calldata = encode_approve(self.morphoAddress, approve_amount)
            transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
            logging.info(f'Added USDC approval tx: USDC -> Morpho for {approve_amount}')
        if borrow_shares > 0:
            repay_calldata = encode_repay(
                loan_token=loan_token,
                collateral_token=collateral,
                oracle=oracle,
                irm=irm,
                lltv=lltv,
                assets=0,
                shares=borrow_shares,
                on_behalf=user,
            )
            transactions.append(TransactionCall(to=self.morphoAddress, data=repay_calldata))
            logging.info(f'Added repay tx: {borrow_shares} borrow shares to Morpho')
        else:
            repay_calldata = encode_repay(
                loan_token=loan_token,
                collateral_token=collateral,
                oracle=oracle,
                irm=irm,
                lltv=lltv,
                assets=repay_amount,
                on_behalf=user,
            )
            transactions.append(TransactionCall(to=self.morphoAddress, data=repay_calldata))
            logging.info(f'Added repay tx: {repay_amount} USDC to Morpho')
        withdraw_collateral_calldata = encode_withdraw_collateral(
            loan_token=loan_token,
            collateral_token=collateral,
            oracle=oracle,
            irm=irm,
            lltv=lltv,
            assets=collateral_amount,
            on_behalf=user,
            receiver=user,
        )
        transactions.append(TransactionCall(to=self.morphoAddress, data=withdraw_collateral_calldata))
        logging.info(f'Added withdraw collateral tx: {collateral_amount} from Morpho')
        return transactions

    def build_vault_deposit_transactions(
        self,
        user_address: str,
        deposit_amount: int,
    ) -> list[TransactionCall]:
        """Build transactions to deposit idle USDC into the Yo vault: approve USDC, then deposit."""
        user = chain_util.normalize_address(user_address)
        transactions: list[TransactionCall] = []
        usdc_approve_calldata = encode_approve(self.yoVaultAddress, deposit_amount)
        transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
        logging.info(f'Added USDC approval tx: USDC -> Yo vault for {deposit_amount}')
        deposit_calldata = encode_vault_deposit(deposit_amount, user)
        transactions.append(TransactionCall(to=self.yoVaultAddress, data=deposit_calldata))
        logging.info(f'Added vault deposit tx: {deposit_amount} USDC to Yo vault')
        return transactions

    def build_auto_borrow_transactions_from_market(
        self,
        user_address: str,
        collateral_address: str,
        borrow_amount: int,
        market: 'MorphoMarket',
        needs_usdc_approval: bool,
    ) -> list[TransactionCall]:
        return self.build_auto_borrow_transactions(
            user_address=user_address,
            collateral_address=collateral_address,
            borrow_amount=borrow_amount,
            loan_token=market.loan_address,
            oracle=market.oracle_address,
            irm=market.irm_address,
            lltv=market.lltv_raw,
            needs_usdc_approval=needs_usdc_approval,
        )

    def build_auto_borrow_transactions(
        self,
        user_address: str,
        collateral_address: str,
        borrow_amount: int,
        loan_token: str,
        oracle: str,
        irm: str,
        lltv: int,
        needs_usdc_approval: bool,
    ) -> list[TransactionCall]:
        """Build transactions for auto-borrow: borrow more USDC, deposit to vault."""
        user = chain_util.normalize_address(user_address)
        collateral = chain_util.normalize_address(collateral_address)
        transactions: list[TransactionCall] = []
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
        if needs_usdc_approval:
            usdc_approve_calldata = encode_approve(self.yoVaultAddress, borrow_amount)
            transactions.append(TransactionCall(to=self.usdcAddress, data=usdc_approve_calldata))
            logging.info(f'Added USDC approval tx: USDC -> Yo vault for {borrow_amount}')
        deposit_calldata = encode_vault_deposit(borrow_amount, user)
        transactions.append(TransactionCall(to=self.yoVaultAddress, data=deposit_calldata))
        logging.info(f'Added vault deposit tx: {borrow_amount} USDC to Yo vault')
        return transactions
