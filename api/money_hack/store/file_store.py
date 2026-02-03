import json
import os
from pathlib import Path

from core import logging
from core.util import file_util
from pydantic import BaseModel

from money_hack.api.v1_resources import Position
from money_hack.api.v1_resources import UserConfig

DATA_DIR = Path(os.environ.get('DATA_DIR', './data'))


class StoredPosition(BaseModel):
    position: Position


class StoredUserConfig(BaseModel):
    user_config: UserConfig


class GenericValue(BaseModel):
    value: str


class FileStore:
    """Simple file-based storage for positions and user configs."""

    def __init__(self, dataDir: Path | None = None) -> None:
        self.dataDir = dataDir or DATA_DIR
        self.positionsDir = self.dataDir / 'positions'
        self.configsDir = self.dataDir / 'configs'

    def _ensure_dirs(self) -> None:
        self.positionsDir.mkdir(parents=True, exist_ok=True)
        self.configsDir.mkdir(parents=True, exist_ok=True)

    def _get_position_path(self, userAddress: str) -> Path:
        return self.positionsDir / f'{userAddress.lower()}.json'

    def _get_config_path(self, userAddress: str) -> Path:
        return self.configsDir / f'{userAddress.lower()}.json'

    async def save_position(self, userAddress: str, position: Position) -> None:
        self._ensure_dirs()
        filePath = self._get_position_path(userAddress)
        stored = StoredPosition(position=position)
        await file_util.write_file(filePath=str(filePath), content=stored.model_dump_json(indent=2))
        logging.info(f'Saved position for {userAddress} to {filePath}')

    async def load_position(self, userAddress: str) -> Position | None:
        filePath = self._get_position_path(userAddress)
        if not filePath.exists():
            return None
        content = await file_util.read_file(filePath=str(filePath))
        stored = StoredPosition.model_validate_json(content)
        logging.info(f'Loaded position for {userAddress} from {filePath}')
        return stored.position

    async def delete_position(self, userAddress: str) -> None:
        filePath = self._get_position_path(userAddress)
        if filePath.exists():
            filePath.unlink()
            logging.info(f'Deleted position for {userAddress}')

    async def save_user_config(self, userAddress: str, config: UserConfig) -> None:
        self._ensure_dirs()
        filePath = self._get_config_path(userAddress)
        stored = StoredUserConfig(user_config=config)
        await file_util.write_file(filePath=str(filePath), content=stored.model_dump_json(indent=2))
        logging.info(f'Saved user config for {userAddress} to {filePath}')

    async def load_user_config(self, userAddress: str) -> UserConfig | None:
        filePath = self._get_config_path(userAddress)
        if not filePath.exists():
            return None
        content = await file_util.read_file(filePath=str(filePath))
        stored = StoredUserConfig.model_validate_json(content)
        return stored.user_config

    async def list_all_positions(self) -> list[Position]:
        self._ensure_dirs()
        positions: list[Position] = []
        for file in self.positionsDir.glob('*.json'):
            content = await file_util.read_file(filePath=str(file))
            stored = StoredPosition.model_validate_json(content)
            positions.append(stored.position)
        return positions

    async def set(self, key: str, value: str | dict[str, object]) -> None:
        self._ensure_dirs()
        filePath = self.dataDir / f'{key}.json'
        jsonContent = json.dumps(value) if isinstance(value, dict) else GenericValue(value=value).model_dump_json()
        await file_util.write_file(filePath=str(filePath), content=jsonContent)

    async def get(self, key: str) -> str | None:
        filePath = self.dataDir / f'{key}.json'
        if not filePath.exists():
            return None
        content = await file_util.read_file(filePath=str(filePath))
        try:
            data = GenericValue.model_validate_json(content)
        except ValueError:
            return content
        else:
            return data.value

    async def delete(self, key: str) -> None:
        filePath = self.dataDir / f'{key}.json'
        if filePath.exists():
            filePath.unlink()
