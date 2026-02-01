from typing import Any

from core.caching.cache import Cache
from core.util import json_util


async def get_json_from_optional_cache(cache: Cache | None, key: str) -> Any | None:  # type: ignore[explicit-any]
    if cache is None:
        return None
    content = await cache.get(key)
    if content is None:
        return None
    return json_util.loads(content)


async def save_json_to_optional_cache(cache: Cache | None, key: str, value: Any, expirySeconds: int) -> None:  # type: ignore[explicit-any]
    if cache is None:
        return
    await cache.set(key=key, value=json_util.dumps(value), expirySeconds=expirySeconds)
