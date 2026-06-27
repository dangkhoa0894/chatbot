"""
In-memory registry of currently active WebSocket sessions.
Tracks which sessions are escalated (user requested human support).
Thread-safe via a single lock; designed for a single-process deployment.
"""
import time
import threading

_lock = threading.Lock()
_sessions: dict[str, dict] = {}


def register(session_id: str) -> None:
    with _lock:
        _sessions[session_id] = {
            "session_id": session_id,
            "connected_at": time.time(),
            "last_activity": time.time(),
            "escalated": False,
            "escalation_reason": "",
            "customer_name": "",
            "customer_phone": "",
            "admin_joined": False,
        }


def unregister(session_id: str) -> None:
    with _lock:
        _sessions.pop(session_id, None)


def touch(session_id: str) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["last_activity"] = time.time()


def flag_escalation(
    session_id: str,
    reason: str,
    customer_name: str = "",
    customer_phone: str = "",
) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id].update({
                "escalated": True,
                "escalation_reason": reason,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
            })


def unflag(session_id: str) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["escalated"] = False
            _sessions[session_id]["admin_joined"] = False


def set_admin_joined(session_id: str, joined: bool) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["admin_joined"] = joined


def get_all() -> list[dict]:
    with _lock:
        return [dict(s) for s in _sessions.values()]


def get(session_id: str) -> dict | None:
    with _lock:
        s = _sessions.get(session_id)
        return dict(s) if s else None
