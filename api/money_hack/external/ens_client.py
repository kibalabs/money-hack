import hashlib
import re

from core import logging
from core.requester import Requester
from pydantic import BaseModel
from web3 import Web3

from money_hack.api.v1_resources import TransactionCall

BORROWBOT_PARENT_NAME = 'borrowbot.eth'
NAME_WRAPPER_ADDRESS = '0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401'
PUBLIC_RESOLVER_ADDRESS = '0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63'

w3 = Web3()


class EnsAgentConfig(BaseModel):
    collateral: str | None = None
    target_ltv: int | None = None
    max_ltv: int | None = None
    min_ltv: int | None = None
    auto_rebalance: bool = True
    risk_tolerance: str = 'medium'
    emoji: str = '🤖'
    description: str | None = None


ENS_NAME_WRAPPER_ABI = [
    {
        'inputs': [
            {'name': 'parentNode', 'type': 'bytes32'},
            {'name': 'label', 'type': 'string'},
            {'name': 'owner', 'type': 'address'},
            {'name': 'fuses', 'type': 'uint16'},
            {'name': 'expiry', 'type': 'uint64'},
        ],
        'name': 'setSubnodeOwner',
        'outputs': [{'name': 'node', 'type': 'bytes32'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'name': 'id', 'type': 'uint256'}],
        'name': 'ownerOf',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

ENS_PUBLIC_RESOLVER_ABI = [
    {
        'inputs': [
            {'name': 'node', 'type': 'bytes32'},
            {'name': 'key', 'type': 'string'},
            {'name': 'value', 'type': 'string'},
        ],
        'name': 'setText',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'name': 'node', 'type': 'bytes32'},
            {'name': 'key', 'type': 'string'},
        ],
        'name': 'text',
        'outputs': [{'name': '', 'type': 'string'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]


def namehash(name: str) -> bytes:
    """Compute ENS namehash for a domain name."""
    if not name:
        return bytes(32)
    labels = name.split('.')
    node = bytes(32)
    for label in reversed(labels):
        labelHash = hashlib.sha3_256(label.encode()).digest()
        node = hashlib.sha3_256(node + labelHash).digest()
    return node


def labelhash(label: str) -> bytes:
    """Compute keccak256 hash of a label."""
    return hashlib.sha3_256(label.encode()).digest()


MIN_LABEL_LENGTH = 3
MAX_LABEL_LENGTH = 32


def is_valid_ens_label(label: str) -> bool:
    """Check if a label is valid for ENS subdomain."""
    if not label or len(label) < MIN_LABEL_LENGTH or len(label) > MAX_LABEL_LENGTH:
        return False
    if not re.match(r'^[a-z0-9-]+$', label.lower()):
        return False
    return not (label.startswith('-') or label.endswith('-'))


class EnsClient:
    """Client for ENS operations - subdomain registration and text record management."""

    def __init__(self, requester: Requester, chainId: int = 1) -> None:
        self.requester = requester
        self.chainId = chainId
        self.parentName = BORROWBOT_PARENT_NAME
        self.parentNode = namehash(BORROWBOT_PARENT_NAME)
        self.nameWrapperAddress = NAME_WRAPPER_ADDRESS
        self.resolverAddress = PUBLIC_RESOLVER_ADDRESS
        self._usedNamesCache: set[str] = set()

    def get_full_ens_name(self, label: str) -> str:
        """Get full ENS name from label."""
        return f'{label.lower()}.{self.parentName}'

    def validate_label(self, label: str) -> tuple[bool, str]:
        """Validate an ENS label for use as agent name."""
        if not is_valid_ens_label(label):
            return False, 'Label must be 3-32 lowercase alphanumeric characters or hyphens, not starting/ending with hyphen'
        if label.lower() in self._usedNamesCache:
            return False, 'Name is already taken'
        return True, ''

    def check_name_available(self, label: str) -> bool:
        """Check if an ENS subdomain is available (cached check only for MVP)."""
        return label.lower() not in self._usedNamesCache

    def reserve_name(self, label: str) -> str:
        """Reserve a name (for MVP, just add to cache and return full ENS name)."""
        self._usedNamesCache.add(label.lower())
        return self.get_full_ens_name(label)

    def build_register_subdomain_transaction(self, label: str, ownerAddress: str) -> TransactionCall:
        """Build transaction to register a subdomain under borrowbot.eth."""
        nameWrapperContract = w3.eth.contract(address=self.nameWrapperAddress, abi=ENS_NAME_WRAPPER_ABI)
        fn = nameWrapperContract.functions.setSubnodeOwner(
            self.parentNode,
            label.lower(),
            Web3.to_checksum_address(ownerAddress),
            0,
            2**64 - 1,
        )
        encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
        calldata = str(encoded) if isinstance(encoded, (bytes, str)) else encoded
        logging.info(f'Built ENS subdomain registration tx: {label}.{self.parentName} -> {ownerAddress}')
        return TransactionCall(to=self.nameWrapperAddress, data=calldata)

    def build_set_text_record_transaction(self, ensName: str, key: str, value: str) -> TransactionCall:
        """Build transaction to set a text record on an ENS name."""
        node = namehash(ensName)
        resolverContract = w3.eth.contract(address=self.resolverAddress, abi=ENS_PUBLIC_RESOLVER_ABI)
        fn = resolverContract.functions.setText(node, key, value)
        encoded = fn.build_transaction({'from': '0x0000000000000000000000000000000000000000'})['data']
        calldata = str(encoded) if isinstance(encoded, (bytes, str)) else encoded
        logging.info(f'Built ENS setText tx: {ensName} {key}={value}')
        return TransactionCall(to=self.resolverAddress, data=calldata)

    def build_set_agent_config_transactions(self, ensName: str, config: EnsAgentConfig) -> list[TransactionCall]:
        """Build transactions to set all agent config text records."""
        transactions: list[TransactionCall] = []
        if config.collateral:
            transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.collateral', config.collateral))
        if config.target_ltv is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.targetLtv', str(config.target_ltv)))
        if config.max_ltv is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.maxLtv', str(config.max_ltv)))
        if config.min_ltv is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.minLtv', str(config.min_ltv)))
        transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.autoRebalance', str(config.auto_rebalance).lower()))
        transactions.append(self.build_set_text_record_transaction(ensName, 'borrowbot.riskTolerance', config.risk_tolerance))
        transactions.append(self.build_set_text_record_transaction(ensName, 'avatar', f'emoji:{config.emoji}'))
        if config.description:
            transactions.append(self.build_set_text_record_transaction(ensName, 'description', config.description))
        return transactions
