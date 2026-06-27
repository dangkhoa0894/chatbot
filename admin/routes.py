import uuid
import time as _time
import hmac
import hashlib
import base64
import json
from fastapi import APIRouter, HTTPException, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict
from config import settings
from db.database import (
    get_token_stats, get_token_logs, get_distinct_agents,
    load_all_products, upsert_product, delete_product,
    get_escalations, resolve_escalation,
)
from services.product_service import reload_products
from services import runtime_config as _rc

router = APIRouter(prefix="/admin/api")

_TOKEN_TTL_HOURS = 8


# ── Pure-Python HS256 JWT (stdlib only) ───────────────────────────────────────
def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def _jwt_encode(payload: dict, secret: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), signing_input, digestmod=hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _jwt_decode(token: str, secret: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure")
        header_b, body_b, sig_b = parts
        signing_input = f"{header_b}.{body_b}".encode()
        expected_sig = hmac.new(secret.encode(), signing_input, digestmod=hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b)):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64url_decode(body_b))
        if payload.get("exp", 0) < _time.time():
            raise ValueError("Token expired")
        return payload
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Token decode error: {exc}") from exc


# ── Auth ───────────────────────────────────────────────────────────────────────
def _make_token() -> str:
    now = int(_time.time())
    payload = {"sub": "admin", "iat": now, "exp": now + _TOKEN_TTL_HOURS * 3600}
    secret = settings.JWT_SECRET or settings.ADMIN_TOKEN or "fallback-dev-secret"
    return _jwt_encode(payload, secret)


def _auth(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = authorization[7:]
    secret = settings.JWT_SECRET or settings.ADMIN_TOKEN or "fallback-dev-secret"
    try:
        _jwt_decode(token, secret)
    except ValueError as exc:
        detail = "Token expired" if "expired" in str(exc) else "Invalid token"
        raise HTTPException(status_code=401, detail=detail)


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginPayload(BaseModel):
    username: str
    password: str


_login_hits: dict = {}


def _check_login_rate(ip: str) -> None:
    now = _time.monotonic()
    hits = [t for t in _login_hits.get(ip, []) if now - t < 60]
    if len(hits) >= 10:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    hits.append(now)
    _login_hits[ip] = hits


@router.post("/login")
def login(body: LoginPayload, request: Request):
    _check_login_rate(request.client.host if request.client else "unknown")
    if body.username == settings.ADMIN_USERNAME and body.password == settings.ADMIN_PASSWORD:
        return {"token": _make_token(), "expires_in": _TOKEN_TTL_HOURS * 3600}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ── Verify token ───────────────────────────────────────────────────────────────
@router.get("/verify")
def verify(authorization: str = Header(None)):
    _auth(authorization)
    return {"ok": True, "expires_in": _TOKEN_TTL_HOURS * 3600}


@router.post("/logout")
def logout(authorization: str = Header(None)):
    _auth(authorization)
    return {"ok": True}


# ── Token stats ────────────────────────────────────────────────────────────────
@router.get("/stats")
def token_stats(days: int = 7, authorization: str = Header(None)):
    _auth(authorization)
    return get_token_stats(days)


@router.get("/logs")
def token_logs(
    limit: int = Query(50, le=200),
    offset: int = 0,
    agent: Optional[str] = None,
    model: Optional[str] = None,
    authorization: str = Header(None),
):
    _auth(authorization)
    return get_token_logs(limit=limit, offset=offset, agent=agent, model=model)


@router.get("/agents")
def list_agents(authorization: str = Header(None)):
    _auth(authorization)
    return get_distinct_agents()


# ── Chatbot Metrics ────────────────────────────────────────────────────────────
@router.get("/metrics")
def get_metrics(hours: int = Query(24, le=168), authorization: str = Header(None)):
    _auth(authorization)
    from services.metrics import metrics
    return metrics.summary(hours)


# ── Runtime Config ─────────────────────────────────────────────────────────────
class ContextConfigPayload(BaseModel):
    window: Optional[int] = None
    compress_at: Optional[int] = None
    max_summary_chars: Optional[int] = None


class LLMModelsPayload(BaseModel):
    intent: Optional[str] = None
    closing: Optional[str] = None
    general: Optional[str] = None
    summarizer: Optional[str] = None


class LLMTokensPayload(BaseModel):
    intent: Optional[int] = None
    closing: Optional[int] = None
    general: Optional[int] = None
    summarizer: Optional[int] = None


class LLMConfigPayload(BaseModel):
    models: Optional[LLMModelsPayload] = None
    max_tokens: Optional[LLMTokensPayload] = None


class ConfigPayload(BaseModel):
    context: Optional[ContextConfigPayload] = None
    llm: Optional[LLMConfigPayload] = None


@router.get("/config")
def get_config(authorization: str = Header(None)):
    _auth(authorization)
    return _rc.get_all()


@router.patch("/config")
def patch_config(payload: ConfigPayload, authorization: str = Header(None)):
    _auth(authorization)
    _rc.update(payload.model_dump(exclude_none=True))
    return _rc.get_all()


# ── Products ───────────────────────────────────────────────────────────────────
class ProductPayload(BaseModel):
    id: Optional[str] = None
    name: str
    brand: str
    category: str
    price: int
    specs: dict[str, Any] = {}
    highlight: str = ""
    use_cases: list[str] = []
    pros: list[str] = []
    cons: list[str] = []
    stock: int = 0
    rating: float = 4.0
    tags: list[str] = []


@router.get("/products")
def get_products(authorization: str = Header(None)):
    _auth(authorization)
    return load_all_products()


@router.post("/products", status_code=201)
def create_product(payload: ProductPayload, authorization: str = Header(None)):
    _auth(authorization)
    p = payload.model_dump()
    if not p.get("id"):
        prefix = {"laptop": "LP", "phone": "PH", "tablet": "TB"}.get(p["category"], "PR")
        p["id"] = prefix + uuid.uuid4().hex[:4].upper()
    upsert_product(p)
    reload_products()
    return {"id": p["id"], "status": "created"}


@router.put("/products/{product_id}")
def update_product(product_id: str, payload: ProductPayload, authorization: str = Header(None)):
    _auth(authorization)
    p = payload.model_dump()
    p["id"] = product_id
    upsert_product(p)
    reload_products()
    return {"id": product_id, "status": "updated"}


@router.delete("/products/{product_id}")
def remove_product(product_id: str, authorization: str = Header(None)):
    _auth(authorization)
    delete_product(product_id)
    reload_products()
    return {"id": product_id, "status": "deleted"}


# ── CSAT ──────────────────────────────────────────────────────────────────────
@router.get("/csat")
def csat_stats(days: int = 7, authorization: str = Header(None)):
    _auth(authorization)
    from db.database import get_csat_stats
    return get_csat_stats(days)


# ── Escalations ────────────────────────────────────────────────────────────────
@router.get("/escalations")
def list_escalations(
    limit: int = Query(50, le=200),
    offset: int = 0,
    resolved: Optional[int] = None,
    authorization: str = Header(None),
):
    _auth(authorization)
    return get_escalations(limit=limit, offset=offset, resolved=resolved)


@router.patch("/escalations/{escalation_id}/resolve")
def mark_resolved(escalation_id: int, authorization: str = Header(None)):
    _auth(authorization)
    resolve_escalation(escalation_id)
    return {"id": escalation_id, "status": "resolved"}


# ── Live Session Monitor ───────────────────────────────────────────────────────
@router.get("/live-sessions")
def get_live_sessions(authorization: str = Header(None)):
    _auth(authorization)
    from services import session_monitor
    return session_monitor.get_all()


class AdminMessagePayload(BaseModel):
    content: str


@router.post("/sessions/{session_id}/accept")
async def accept_session(
    session_id: str,
    authorization: str = Header(None),
):
    """Admin explicitly takes ownership — notifies user and mutes the bot."""
    _auth(authorization)
    from channels.websocket_handler import manager
    from services import session_monitor
    from services import session_store

    info = session_monitor.get(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Session not active")
    if info.get("admin_joined"):
        return {"ok": True, "already_joined": True}

    session_monitor.set_admin_joined(session_id, True)

    _JOIN_MSG = "Xin chào! Nhân viên hỗ trợ TechShop AI đã tiếp nhận. Tôi sẽ giúp bạn ngay!"
    await manager.send(session_id, {
        "type": "human_message",
        "content": _JOIN_MSG,
        "agent_name": "Nhân viên hỗ trợ",
    })

    state = await session_store.get_session(session_id) or {}
    msgs = state.get("messages", [])
    msgs.append({"role": "support", "content": _JOIN_MSG})
    state["messages"] = msgs
    await session_store.save_session(session_id, state)

    return {"ok": True, "already_joined": False}


@router.post("/sessions/{session_id}/message")
async def send_to_session(
    session_id: str,
    body: AdminMessagePayload,
    authorization: str = Header(None),
):
    _auth(authorization)
    from channels.websocket_handler import manager
    from services import session_monitor
    from services import session_store

    info = session_monitor.get(session_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Session not active")

    await manager.send(session_id, {
        "type": "human_message",
        "content": body.content,
        "agent_name": "Nhân viên hỗ trợ",
    })

    session_monitor.set_admin_joined(session_id, True)

    state = await session_store.get_session(session_id) or {}
    msgs = state.get("messages", [])
    msgs.append({"role": "support", "content": body.content})
    state["messages"] = msgs
    await session_store.save_session(session_id, state)

    return {"ok": True}


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    authorization: str = Header(None),
):
    _auth(authorization)
    from services import session_store

    state = await session_store.get_session(session_id)
    if state is None:
        return {"session_id": session_id, "history": []}
    return {"session_id": session_id, "history": state.get("messages", [])}


@router.post("/sessions/{session_id}/resolve")
def resolve_session_escalation(
    session_id: str,
    authorization: str = Header(None),
):
    _auth(authorization)
    from services import session_monitor
    session_monitor.unflag(session_id)
    return {"ok": True, "session_id": session_id}
