import typing

from core.exceptions import KibaException
from core.util.typing_util import JsonObject
from core.web3.eth_client import EncodedCall
from web3.types import LogReceipt
from web3.types import TxReceipt


class UserOperation(typing.TypedDict):
    sender: str
    nonce: str
    initCode: str
    callData: str
    callGasLimit: str
    verificationGasLimit: str
    preVerificationGas: str
    maxFeePerGas: str
    maxPriorityFeePerGas: str
    paymasterAndData: str
    signature: str


class UserOperationReceipt(typing.TypedDict):
    userOpHash: str
    entryPoint: str
    sender: str
    nonce: str
    paymaster: str
    actualGasCost: str
    actualGasUsed: str
    success: bool
    reason: str
    logs: list[LogReceipt]
    receipt: TxReceipt


class UserOperationFailedException(KibaException):
    def __init__(self, receipt: UserOperationReceipt) -> None:
        super().__init__(message='Transaction failed')
        self.receipt = receipt

    def to_dict(self) -> JsonObject:
        output = super().to_dict()
        typing.cast(JsonObject, output['fields'])['receipt'] = typing.cast(JsonObject, self.receipt)
        return output


class SmartWallet(typing.Protocol):
    async def build_execute_call_data(self, chainId: int, calls: list[EncodedCall]) -> str: ...
    async def validate_calls(self, calls: list[EncodedCall], chainId: int) -> None: ...
    def encode_user_operation_signature(self, signature: str) -> str: ...


class Bundler(typing.Protocol):
    async def prepare_user_operation_for_signing(self, sender: str, callData: str) -> UserOperation: ...
    async def build_user_operation(
        self,
        chainId: int,
        sender: str,
        callData: str,
        shouldSponsorGas: bool = True,
        context: JsonObject | None = None,
        presignedSignature: str | None = None,
    ) -> UserOperation: ...
    async def generate_user_operation_hash(self, userOperation: UserOperation) -> str: ...
    async def send_user_operation(self, userOperation: UserOperation, signature: str | None = None) -> str: ...
    async def wait_for_user_operation_receipt(
        self,
        userOperationHash: str,
        sleepSeconds: int = 2,
        maxWaitSeconds: int = 120,
        raiseOnFailure: bool = True,
    ) -> UserOperationReceipt: ...
    def validate_calls(self, calls: list[EncodedCall], chainId: int) -> None: ...
