"""
In-memory registry of currently active WebSocket sessions.
Tracks which sessions are escalated (user requested human support).
Thread-safe via a single lock; designed for a single-process deployment.

_sessions     — active (connected) sessions; cleared on disconnect
_persistent   — escalation/admin state that SURVIVES disconnect so that
                reconnecting users are correctly restored to escalated state
"""
import time
import threading

_lock = threading.Lock()
_sessions: dict[str, dict] = {}
_persistent: dict[str, dict] = {}   # keyed by session_id; not cleared by unregister()


def register(session_id: str) -> None:
    """Register a newly connected (or reconnected) session.

    If the session has a prior persistent escalation record, restore it so the
    admin monitor continues showing it as escalated after a reconnect.
    """
    with _lock:
        saved = _persistent.get(session_id, {})
        _sessions[session_id] = {
            "session_id": session_id,
            "connected_at": time.time(),
            "last_activity": time.time(),
            # Restore from persistent record if it exists
            "escalated": saved.get("escalated", False),
            "escalation_reason": saved.get("escalation_reason", ""),
            "customer_name": saved.get("customer_name", ""),
            "customer_phone": saved.get("customer_phone", ""),
            "admin_joined": saved.get("admin_joined", False),
            "ai_enabled": saved.get("ai_enabled", True),
        }


def unregister(session_id: str) -> None:
    """Remove from active sessions. Persistent escalation record is kept."""
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
    """Flag a session as needing human support.

    Writes to both _sessions (for live display) and _persistent (so it
    survives a reconnect if the user disconnects before admin responds).
    """
    data = {
        "escalated": True,
        "escalation_reason": reason,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
    }
    with _lock:
        _persistent.setdefault(session_id, {}).update(data)
        if session_id in _sessions:
            _sessions[session_id].update(data)


def unflag(session_id: str) -> None:
    """Mark a session as resolved. Clears both live and persistent state."""
    with _lock:
        _persistent.pop(session_id, None)
        if session_id in _sessions:
            _sessions[session_id]["escalated"] = False
            _sessions[session_id]["admin_joined"] = False
            _sessions[session_id]["escalation_reason"] = ""
            _sessions[session_id]["ai_enabled"] = True


def set_admin_joined(session_id: str, joined: bool) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["admin_joined"] = joined
            if joined:
                _sessions[session_id]["ai_enabled"] = False
        p = _persistent.setdefault(session_id, {})
        p["admin_joined"] = joined
        if joined:
            p["ai_enabled"] = False


def set_ai_enabled(session_id: str, enabled: bool) -> None:
    with _lock:
        if session_id in _sessions:
            _sessions[session_id]["ai_enabled"] = enabled
        _persistent.setdefault(session_id, {})["ai_enabled"] = enabled


def is_ai_enabled(session_id: str) -> bool:
    """Return True if the AI bot should respond for this session (default True)."""
    with _lock:
        s = _sessions.get(session_id)
        if s is None:
            return True
        return bool(s.get("ai_enabled", True))


def get_all() -> list[dict]:
    with _lock:
        return [dict(s) for s in _sessions.values()]


def get(session_id: str) -> dict | None:
    with _lock:
        s = _sessions.get(session_id)
        return dict(s) if s else None


def is_admin_handling(session_id: str) -> bool:
    """Return True if an admin has taken over this session (bot should be muted)."""
    with _lock:
        s = _sessions.get(session_id)
        return bool(s and s.get("admin_joined"))
