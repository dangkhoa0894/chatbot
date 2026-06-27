"""Redis-backed session store with transparent fallback to in-memory dict."""
import json
from typing import Optional
from collections import OrderedDict
from config import settings


class _LRUDict:
    def __init__(self, maxsize: int):
        self._d: OrderedDict = OrderedDict()
        self._max = maxsize
    def get(self, key: str):
        if key not in self._d:
            return None
        self._d.move_to_end(key)
        return self._d[key]
    def set(self, key: str, value):
        if key in self._d:
            self._d.move_to_end(key)
        self._d[key] = value
        if len(self._d) > self._max:
            self._d.popitem(last=False)
    def pop(self, key: str, default=None):
        return self._d.pop(key, default)
    def __len__(self):
        return len(self._d)
    def __contains__(self, key: str):
        return key in self._d


_MAX_FALLBACK = 5000
_fallback = _LRUDict(_MAX_FALLBACK)
_redis = None


async def _get_redis():
    global _redis
    if not settings.REDIS_URL:
        return None
    if _redis is None:
        try:
            import redis.asyncio as aioredis
            _redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _redis.ping()
        except Exception:
            _redis = None
    return _redis


async def get_session(session_id: str) -> Optional[dict]:
    r = await _get_redis()
    if r:
        try:
            data = await r.get(f"session:{session_id}")
            return json.loads(data) if data else None
        except Exception:
            pass
    return _fallback.get(session_id)


async def save_session(session_id: str, state: dict, ttl: int = 3600):
    clean = {k: v for k, v in state.items() if not k.startswith("_")}
    r = await _get_redis()
    if r:
        try:
            await r.setex(
                f"session:{session_id}",
                ttl,
                json.dumps(clean, ensure_ascii=False, default=str),
            )
            _fallback.pop(session_id, None)
            return
        except Exception:
            pass
    _fallback.set(session_id, clean)


async def delete_session(session_id: str):
    r = await _get_redis()
    if r:
        try:
            await r.delete(f"session:{session_id}")
        except Exception:
            pass
    _fallback.pop(session_id, None)
