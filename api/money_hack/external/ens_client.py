import re

from core import logging
from core.requester import Requester
from core.web3.eth_client import ABI
from core.web3.eth_client import RestEthClient
from pydantic import BaseModel
from web3 import Web3

from money_hack.api.v1_resources import TransactionCall

# Mainnet ENS
ENS_REGISTRY_ADDRESS = '0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e'
ENS_PUBLIC_RESOLVER_ADDRESS = '0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63'
ENS_NAME_WRAPPER_ADDRESS = '0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401'
PARENT_NAME = 'borrowbott.eth'

w3 = Web3()

# Constitution keys (owner sets, agent reads)
CONSTITUTION_KEYS = {
    'max_ltv': 'com.borrowbot.max-ltv',
    'min_spread': 'com.borrowbot.min-spread',
    'max_position_usd': 'com.borrowbot.max-position-usd',
    'allowed_collateral': 'com.borrowbot.allowed-collateral',
    'pause': 'com.borrowbot.pause',
}

# Status keys (agent writes, world reads)
STATUS_KEYS = {
    'status': 'com.borrowbot.status',
    'last_action': 'com.borrowbot.last-action',
    'last_check': 'com.borrowbot.last-check',
}


class EnsConstitution(BaseModel):
    """Agent constitution — guardrails set by the owner via ENS text records."""

    max_ltv: float | None = None
    min_spread: float | None = None
    max_position_usd: float | None = None
    allowed_collateral: str | None = None
    pause: bool = False


class EnsAgentStatus(BaseModel):
    """Agent status — written by the agent to ENS after each check cycle."""

    status: str | None = None
    last_action: str | None = None
    last_check: str | None = None


# Keep old model for backwards compat with existing get_ens_config_transactions
class EnsAgentConfig(BaseModel):
    collateral: str | None = None
    target_ltv: int | None = None
    max_ltv: int | None = None
    min_ltv: int | None = None
    auto_rebalance: bool = True
    risk_tolerance: str = 'medium'
    emoji: str = '🤖'
    description: str | None = None


ENS_RESOLVER_ABI: ABI = [
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
    {
        'inputs': [{'name': 'data', 'type': 'bytes[]'}],
        'name': 'multicall',
        'outputs': [{'name': 'results', 'type': 'bytes[]'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
]

ENS_REGISTRY_ABI: ABI = [
    {
        'inputs': [{'name': 'node', 'type': 'bytes32'}],
        'name': 'owner',
        'outputs': [{'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

ENS_NAME_WRAPPER_ABI: ABI = [
    {
        'inputs': [
            {'name': 'parentNode', 'type': 'bytes32'},
            {'name': 'label', 'type': 'string'},
            {'name': 'owner', 'type': 'address'},
            {'name': 'resolver', 'type': 'address'},
            {'name': 'ttl', 'type': 'uint64'},
            {'name': 'fuses', 'type': 'uint32'},
            {'name': 'expiry', 'type': 'uint64'},
        ],
        'name': 'setSubnodeRecord',
        'outputs': [{'name': 'node', 'type': 'bytes32'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'name': 'id', 'type': 'uint256'}],
        'name': 'ownerOf',
        'outputs': [{'name': 'owner', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'name': 'id', 'type': 'uint256'}],
        'name': 'getData',
        'outputs': [
            {'name': 'owner', 'type': 'address'},
            {'name': 'fuses', 'type': 'uint32'},
            {'name': 'expiry', 'type': 'uint64'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
]


def namehash(name: str) -> bytes:
    """Compute ENS namehash using keccak256."""
    if not name:
        return bytes(32)
    labels = name.split('.')
    node = bytes(32)
    for label in reversed(labels):
        label_hash = w3.keccak(text=label)
        node = w3.keccak(node + label_hash)
    return node


def labelhash(label: str) -> bytes:
    """Compute keccak256 hash of a label."""
    return bytes(w3.keccak(text=label))


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
    """Client for ENS operations — text records via ENS Public Resolver."""

    def __init__(self, requester: Requester, chainId: int = 1) -> None:
        self.requester = requester
        self.chainId = chainId
        self.resolverAddress = ENS_PUBLIC_RESOLVER_ADDRESS
        self._usedNamesCache: set[str] = set()

    def get_full_ens_name(self, label: str) -> str:
        """Get full ENS name from label (subname under borrowbott.eth)."""
        return f'{label.lower()}.{PARENT_NAME}'

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

    def build_register_subname_transaction(self, label: str, ownerAddress: str, expiry: int = 0) -> TransactionCall:
        """Build transaction to register a subname under borrowbott.eth via NameWrapper.

        Uses NameWrapper.setSubnodeRecord so ENS UIs resolve the human-readable label.
        Must be sent by the NameWrapper token owner of borrowbott.eth (the deployer).
        """
        parentNode = namehash(PARENT_NAME)
        wrapperContract = w3.eth.contract(
            address=Web3.to_checksum_address(ENS_NAME_WRAPPER_ADDRESS),
            abi=ENS_NAME_WRAPPER_ABI,
        )
        fn = wrapperContract.functions.setSubnodeRecord(
            parentNode,
            label.lower(),
            Web3.to_checksum_address(ownerAddress),
            Web3.to_checksum_address(self.resolverAddress),
            0,       # ttl
            0,       # fuses (no restrictions)
            expiry,  # expiry (0 = max allowed by parent)
        )
        encoded = fn._encode_transaction_data()
        calldata = str(encoded) if isinstance(encoded, (bytes, str)) else encoded
        logging.info(f'Built ENS NameWrapper setSubnodeRecord tx: {label}.{PARENT_NAME} -> {ownerAddress}')
        return TransactionCall(to=ENS_NAME_WRAPPER_ADDRESS, data=calldata)

    def build_set_text_record_transaction(self, ensName: str, key: str, value: str) -> TransactionCall:
        """Build transaction to set a text record on an ENS name via Public Resolver."""
        node = namehash(ensName)
        resolverContract = w3.eth.contract(address=Web3.to_checksum_address(self.resolverAddress), abi=ENS_RESOLVER_ABI)
        fn = resolverContract.functions.setText(node, key, value)
        encoded = fn._encode_transaction_data()
        calldata = str(encoded) if isinstance(encoded, (bytes, str)) else encoded
        logging.info(f'Built ENS setText tx: {ensName} {key}={value}')
        return TransactionCall(to=self.resolverAddress, data=calldata)

    def build_set_agent_config_transactions(self, ensName: str, config: EnsAgentConfig) -> list[TransactionCall]:
        """Build transactions to set all agent config text records (legacy)."""
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

    # --- Constitution (owner-set guardrails) ---

    async def read_text_record(self, ethClient: RestEthClient, ensName: str, key: str) -> str:
        """Read a single text record from the L2Resolver."""
        node = namehash(ensName)
        response = await ethClient.call_function_by_name(
            toAddress=self.resolverAddress,
            contractAbi=ENS_RESOLVER_ABI,
            functionName='text',
            arguments={'node': node, 'key': key},
        )
        return str(response[0]) if response[0] else ''

    async def read_constitution(self, ethClient: RestEthClient, ensName: str) -> EnsConstitution:
        """Read the agent's constitution from ENS text records."""
        values: dict[str, str] = {}
        for field, key in CONSTITUTION_KEYS.items():
            try:
                values[field] = await self.read_text_record(ethClient, ensName, key)
            except Exception:  # noqa: BLE001
                logging.exception(f'Failed to read ENS text record {key} for {ensName}')
                values[field] = ''
        return EnsConstitution(
            max_ltv=float(values['max_ltv']) if values['max_ltv'] else None,
            min_spread=float(values['min_spread']) if values['min_spread'] else None,
            max_position_usd=float(values['max_position_usd']) if values['max_position_usd'] else None,
            allowed_collateral=values['allowed_collateral'] or None,
            pause=values['pause'].lower() == 'true' if values['pause'] else False,
        )

    async def read_status(self, ethClient: RestEthClient, ensName: str) -> EnsAgentStatus:
        """Read the agent's status from ENS text records."""
        values: dict[str, str] = {}
        for field, key in STATUS_KEYS.items():
            try:
                values[field] = await self.read_text_record(ethClient, ensName, key)
            except Exception:  # noqa: BLE001
                logging.exception(f'Failed to read ENS status record {key} for {ensName}')
                values[field] = ''
        return EnsAgentStatus(
            status=values['status'] or None,
            last_action=values['last_action'] or None,
            last_check=values['last_check'] or None,
        )

    # --- Constitution writes (owner sets guardrails) ---

    def build_constitution_transactions(self, ensName: str, constitution: EnsConstitution) -> list[TransactionCall]:
        """Build transactions to set constitution text records."""
        transactions: list[TransactionCall] = []
        if constitution.max_ltv is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, CONSTITUTION_KEYS['max_ltv'], str(constitution.max_ltv)))
        if constitution.min_spread is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, CONSTITUTION_KEYS['min_spread'], str(constitution.min_spread)))
        if constitution.max_position_usd is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, CONSTITUTION_KEYS['max_position_usd'], str(constitution.max_position_usd)))
        if constitution.allowed_collateral is not None:
            transactions.append(self.build_set_text_record_transaction(ensName, CONSTITUTION_KEYS['allowed_collateral'], constitution.allowed_collateral))
        transactions.append(self.build_set_text_record_transaction(ensName, CONSTITUTION_KEYS['pause'], str(constitution.pause).lower()))
        return transactions

    # --- Status writes (agent reports back) ---

    def build_status_update_transactions(self, ensName: str, status: str, lastAction: str, lastCheck: str) -> list[TransactionCall]:
        """Build transactions for the agent to write its status to ENS."""
        return [
            self.build_set_text_record_transaction(ensName, STATUS_KEYS['status'], status),
            self.build_set_text_record_transaction(ensName, STATUS_KEYS['last_action'], lastAction),
            self.build_set_text_record_transaction(ensName, STATUS_KEYS['last_check'], lastCheck),
        ]

    # --- Multicall (batch multiple setText into one transaction for mainnet) ---

    def build_multicall_transaction(self, ensName: str, records: dict[str, str]) -> TransactionCall:
        """Build a single multicall transaction that sets multiple text records at once.

        This batches all setText calls into one resolver.multicall() — one transaction on mainnet.
        """
        node = namehash(ensName)
        resolverContract = w3.eth.contract(address=Web3.to_checksum_address(self.resolverAddress), abi=ENS_RESOLVER_ABI)
        encoded_calls: list[bytes] = []
        for key, value in records.items():
            calldata = resolverContract.functions.setText(node, key, value)._encode_transaction_data()
            encoded_calls.append(bytes.fromhex(calldata[2:]) if isinstance(calldata, str) else calldata)
        multicallData = resolverContract.functions.multicall(encoded_calls)._encode_transaction_data()
        logging.info(f'Built ENS multicall tx: {ensName} with {len(encoded_calls)} setText calls')
        return TransactionCall(to=self.resolverAddress, data=str(multicallData))

    def build_constitution_multicall(self, ensName: str, constitution: EnsConstitution) -> TransactionCall:
        """Build a single multicall to set all constitution text records."""
        records: dict[str, str] = {}
        if constitution.max_ltv is not None:
            records[CONSTITUTION_KEYS['max_ltv']] = str(constitution.max_ltv)
        if constitution.min_spread is not None:
            records[CONSTITUTION_KEYS['min_spread']] = str(constitution.min_spread)
        if constitution.max_position_usd is not None:
            records[CONSTITUTION_KEYS['max_position_usd']] = str(constitution.max_position_usd)
        if constitution.allowed_collateral is not None:
            records[CONSTITUTION_KEYS['allowed_collateral']] = constitution.allowed_collateral
        records[CONSTITUTION_KEYS['pause']] = str(constitution.pause).lower()
        return self.build_multicall_transaction(ensName, records)

    def build_full_constitution_multicall(
        self,
        ensName: str,
        constitution: EnsConstitution,
        status: str,
        lastAction: str,
        lastCheck: str,
    ) -> TransactionCall:
        """Build a single multicall for constitution + status records (saves gas on mainnet)."""
        records: dict[str, str] = {}
        if constitution.max_ltv is not None:
            records[CONSTITUTION_KEYS['max_ltv']] = str(constitution.max_ltv)
        if constitution.min_spread is not None:
            records[CONSTITUTION_KEYS['min_spread']] = str(constitution.min_spread)
        if constitution.max_position_usd is not None:
            records[CONSTITUTION_KEYS['max_position_usd']] = str(constitution.max_position_usd)
        if constitution.allowed_collateral is not None:
            records[CONSTITUTION_KEYS['allowed_collateral']] = constitution.allowed_collateral
        records[CONSTITUTION_KEYS['pause']] = str(constitution.pause).lower()
        records[STATUS_KEYS['status']] = status
        records[STATUS_KEYS['last_action']] = lastAction
        records[STATUS_KEYS['last_check']] = lastCheck
        return self.build_multicall_transaction(ensName, records)
