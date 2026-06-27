"""Redis-backed session store with transparent fallback to in-memory dict."""
import json
from typing import Optional
from config import settings

_fallback: dict = {}
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
    _fallback[session_id] = clean


async def delete_session(session_id: str):
    r = await _get_redis()
    if r:
        try:
            await r.delete(f"session:{session_id}")
        except Exception:
            pass
    _fallback.pop(session_id, None)
