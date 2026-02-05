from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypeVar

import yaml  # type: ignore[import-untyped]
from core import logging
from core.exceptions import KibaException
from pydantic import BaseModel

if TYPE_CHECKING:
    from money_hack.agent.runtime_state import RuntimeState


class ChatToolInput(BaseModel):
    """Base class for chat tool input parameters."""


ParamsType = TypeVar('ParamsType', bound=ChatToolInput)
RuntimeStateType = TypeVar('RuntimeStateType', bound='RuntimeState')
_ModelType = TypeVar('_ModelType', bound=BaseModel)


class ChatTool[ParamsType, RuntimeStateType](BaseModel):
    """Base class for chat tools that the agent can use."""

    name: str
    description: str
    paramsSchema: type[ParamsType]

    async def execute_inner(self, runtimeState: RuntimeStateType, params: ParamsType) -> str:
        """Override this method to implement tool logic."""
        raise NotImplementedError('Subclasses must implement execute_inner')

    async def execute(self, runtimeState: RuntimeStateType, params: ParamsType) -> str:
        """Execute the tool with error handling."""
        try:
            return await self.execute_inner(runtimeState=runtimeState, params=params)
        except KibaException as exception:
            logging.exception(exception)
            return f'Error during {self.name}: {exception.exceptionType} ({exception.message})'
        except Exception as exception:  # noqa: BLE001
            logging.exception(exception)
            return f'Error during {self.name}: {exception!s}'

    def model_to_markdown_yaml(self, model: _ModelType) -> str:
        """Convert a Pydantic model to YAML in a markdown code block."""
        return self.data_to_markdown_yaml(data=model.model_dump())

    def models_to_markdown_yaml(self, models: list[_ModelType]) -> str:
        """Convert a list of Pydantic models to YAML in a markdown code block."""
        return self.data_to_markdown_yaml(data=[model.model_dump() for model in models])

    def data_to_markdown_yaml(self, data: object) -> str:
        """Convert data to YAML in a markdown code block."""
        return f'```yaml\n{yaml.dump(data=data, default_flow_style=False, sort_keys=False)}\n```'
