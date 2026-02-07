# mypy: disable-error-code="typeddict-unknown-key, misc, list-item, typeddict-item"

from eth_typing import ABI

ERC20_ABI: ABI = [
    {
        'inputs': [
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'amount', 'type': 'uint256'},
        ],
        'name': 'approve',
        'outputs': [{'internalType': 'bool', 'name': '', 'type': 'bool'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'address', 'name': 'owner', 'type': 'address'},
            {'internalType': 'address', 'name': 'spender', 'type': 'address'},
        ],
        'name': 'allowance',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

MORPHO_BLUE_ABI: ABI = [
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'address', 'name': 'loanToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'collateralToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'oracle', 'type': 'address'},
                    {'internalType': 'address', 'name': 'irm', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'lltv', 'type': 'uint256'},
                ],
                'internalType': 'struct MarketParams',
                'name': 'marketParams',
                'type': 'tuple',
            },
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'onBehalf', 'type': 'address'},
            {'internalType': 'bytes', 'name': 'data', 'type': 'bytes'},
        ],
        'name': 'supplyCollateral',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'address', 'name': 'loanToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'collateralToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'oracle', 'type': 'address'},
                    {'internalType': 'address', 'name': 'irm', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'lltv', 'type': 'uint256'},
                ],
                'internalType': 'struct MarketParams',
                'name': 'marketParams',
                'type': 'tuple',
            },
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'onBehalf', 'type': 'address'},
            {'internalType': 'address', 'name': 'receiver', 'type': 'address'},
        ],
        'name': 'borrow',
        'outputs': [
            {'internalType': 'uint256', 'name': 'assetsBorrowed', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'sharesBorrowed', 'type': 'uint256'},
        ],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'address', 'name': 'loanToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'collateralToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'oracle', 'type': 'address'},
                    {'internalType': 'address', 'name': 'irm', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'lltv', 'type': 'uint256'},
                ],
                'internalType': 'struct MarketParams',
                'name': 'marketParams',
                'type': 'tuple',
            },
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'onBehalf', 'type': 'address'},
            {'internalType': 'bytes', 'name': 'data', 'type': 'bytes'},
        ],
        'name': 'repay',
        'outputs': [
            {'internalType': 'uint256', 'name': 'assetsRepaid', 'type': 'uint256'},
            {'internalType': 'uint256', 'name': 'sharesRepaid', 'type': 'uint256'},
        ],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'address', 'name': 'loanToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'collateralToken', 'type': 'address'},
                    {'internalType': 'address', 'name': 'oracle', 'type': 'address'},
                    {'internalType': 'address', 'name': 'irm', 'type': 'address'},
                    {'internalType': 'uint256', 'name': 'lltv', 'type': 'uint256'},
                ],
                'internalType': 'struct MarketParams',
                'name': 'marketParams',
                'type': 'tuple',
            },
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'onBehalf', 'type': 'address'},
            {'internalType': 'address', 'name': 'receiver', 'type': 'address'},
        ],
        'name': 'withdrawCollateral',
        'outputs': [],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bytes32', 'name': 'id', 'type': 'bytes32'}],
        'name': 'market',
        'outputs': [
            {'internalType': 'uint128', 'name': 'totalSupplyAssets', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'totalSupplyShares', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'totalBorrowAssets', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'totalBorrowShares', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'lastUpdate', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'fee', 'type': 'uint128'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'bytes32', 'name': 'id', 'type': 'bytes32'},
            {'internalType': 'address', 'name': 'user', 'type': 'address'},
        ],
        'name': 'position',
        'outputs': [
            {'internalType': 'uint256', 'name': 'supplyShares', 'type': 'uint256'},
            {'internalType': 'uint128', 'name': 'borrowShares', 'type': 'uint128'},
            {'internalType': 'uint128', 'name': 'collateral', 'type': 'uint128'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'bytes32', 'name': 'id', 'type': 'bytes32'}],
        'name': 'idToMarketParams',
        'outputs': [
            {'internalType': 'address', 'name': 'loanToken', 'type': 'address'},
            {'internalType': 'address', 'name': 'collateralToken', 'type': 'address'},
            {'internalType': 'address', 'name': 'oracle', 'type': 'address'},
            {'internalType': 'address', 'name': 'irm', 'type': 'address'},
            {'internalType': 'uint256', 'name': 'lltv', 'type': 'uint256'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    },
]

ERC4626_VAULT_ABI: ABI = [
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'receiver', 'type': 'address'},
        ],
        'name': 'deposit',
        'outputs': [{'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'receiver', 'type': 'address'},
            {'internalType': 'address', 'name': 'owner', 'type': 'address'},
        ],
        'name': 'withdraw',
        'outputs': [{'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [
            {'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'},
            {'internalType': 'address', 'name': 'receiver', 'type': 'address'},
            {'internalType': 'address', 'name': 'owner', 'type': 'address'},
        ],
        'name': 'redeem',
        'outputs': [{'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'}],
        'stateMutability': 'nonpayable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'owner', 'type': 'address'}],
        'name': 'maxWithdraw',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'}],
        'name': 'convertToAssets',
        'outputs': [{'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'uint256', 'name': 'assets', 'type': 'uint256'}],
        'name': 'convertToShares',
        'outputs': [{'internalType': 'uint256', 'name': 'shares', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [],
        'name': 'asset',
        'outputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]
