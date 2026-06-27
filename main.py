from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as _BM

from channels.websocket_handler import websocket_endpoint
from channels.messenger_handler import router as messenger_router
from admin.routes import router as admin_router
from services.product_service import PRODUCTS_DB, search_products, format_price, reload_products
from graph.orchestrator import get_session_state, clear_session
from db.database import init_db, seed_products_if_empty
from services.rate_limiter import rate_limiter
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from services.logger import setup_logging
    setup_logging()
    import logging
    _log = logging.getLogger("startup")
    from config import validate_config
    try:
        validate_config()
    except RuntimeError as e:
        _log.critical("STARTUP FAILED — %s", e)
        raise
    init_db()
    seed_products_if_empty(PRODUCTS_DB)
    reload_products()
    # Apply rate limit settings from config
    rate_limiter.max_requests = settings.RATE_LIMIT_REQUESTS
    rate_limiter.window = settings.RATE_LIMIT_WINDOW
    if settings.ADMIN_TOKEN == "admin123":
        print("⚠️  ADMIN_TOKEN is default 'admin123'. Set ADMIN_TOKEN in .env for production.")
    yield


app = FastAPI(
    title="TechShop AI Chatbot",
    description="Multi-agent e-commerce chatbot — laptop, phone, tablet",
    version="3.0.0",
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()] if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
except ImportError:
    pass

# ── Static files ───────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

# ── Facebook Messenger webhook ─────────────────────────────────────────────────
app.include_router(messenger_router, tags=["Facebook Messenger"])

# ── Admin API ──────────────────────────────────────────────────────────────────
app.include_router(admin_router, tags=["Admin"])

# ── REST: Simulated product API ────────────────────────────────────────────────
@app.get("/api/products", tags=["Products"])
async def list_products(
    category: str = None, brand: str = None,
    max_price: int = None, min_price: int = None,
    use_case: str = None, q: str = None,
):
    results = search_products(
        category=category, brand=brand, max_price=max_price,
        min_price=min_price, use_case=use_case, keywords=[q] if q else [],
    )
    return {"total": len(results), "products": [{**p, "price_display": format_price(p["price"])} for p in results]}


@app.get("/api/products/{product_id}", tags=["Products"])
async def get_product(product_id: str):
    from services.product_service import get_product_by_id
    p = get_product_by_id(product_id)
    if not p:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return {**p, "price_display": format_price(p["price"])}


# ── Session ────────────────────────────────────────────────────────────────────
@app.get("/api/session/{session_id}", tags=["Session"])
async def session_state(session_id: str):
    return await get_session_state(session_id)

@app.delete("/api/session/{session_id}", tags=["Session"])
async def end_session(session_id: str):
    await clear_session(session_id)
    return {"status": "cleared"}


# ── CSAT ──────────────────────────────────────────────────────────────────────
class CsatPayload(_BM):
    session_id: str
    rating: int  # 1 or 5
    comment: str = ""
    context: str = ""
    turn_count: int = 0


@app.post("/api/csat", tags=["CSAT"])
async def submit_csat(body: CsatPayload):
    from db.database import log_csat
    if body.rating not in (1, 5):
        return JSONResponse({"error": "rating must be 1 or 5"}, status_code=400)
    log_csat(body.session_id, body.rating, body.comment, body.context, body.turn_count)
    return {"status": "ok"}


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    import logging as _logging
    _hlog = _logging.getLogger("health")
    result = {"ok": True, "checks": {}}

    # DB check
    try:
        from db.database import _conn
        with _conn() as c:
            c.execute("SELECT 1").fetchone()
        result["checks"]["db"] = "ok"
    except Exception as e:
        result["checks"]["db"] = f"error: {e}"
        result["ok"] = False
        _hlog.error("Health DB check failed: %s", e)

    # Redis check
    try:
        from services import session_store
        r = await session_store._get_redis()
        if r:
            await r.ping()
            result["checks"]["redis"] = "ok"
        else:
            result["checks"]["redis"] = "not_configured"
    except Exception as e:
        result["checks"]["redis"] = f"error: {e}"

    # Products check
    from services.product_service import PRODUCTS_DB
    result["checks"]["products"] = len(PRODUCTS_DB)

    if not result["ok"]:
        return JSONResponse(result, status_code=503)
    return result


import os as _os

@app.get("/version", include_in_schema=False)
async def version():
    return {
        "version": app.version,
        "git_commit": _os.getenv("GIT_COMMIT", "unknown"),
        "build_date": _os.getenv("BUILD_DATE", "unknown"),
    }


# ── Pages ──────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse, tags=["UI"])
async def admin_ui():
    with open("static/admin.html", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
