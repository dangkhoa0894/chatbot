import uuid
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict
from config import settings
from db.database import (
    get_token_stats, get_token_logs, get_distinct_agents,
    load_all_products, upsert_product, delete_product,
)
from services.product_service import reload_products
from services import runtime_config as _rc

router = APIRouter(prefix="/admin/api")


# ── Auth ───────────────────────────────────────────────────────────────────────
def _auth(authorization: str | None):
    if not authorization or authorization != f"Bearer {settings.ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginPayload):
    if body.username == settings.ADMIN_USERNAME and body.password == settings.ADMIN_PASSWORD:
        return {"token": settings.ADMIN_TOKEN}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ── Verify token ───────────────────────────────────────────────────────────────
@router.get("/verify")
def verify(authorization: str = Header(None)):
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
