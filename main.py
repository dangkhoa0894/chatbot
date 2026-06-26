from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from channels.websocket_handler import websocket_endpoint
from channels.messenger_handler import router as messenger_router
from services.product_service import PRODUCTS_DB, search_products, format_price
from graph.orchestrator import get_session_state, clear_session
from config import settings

app = FastAPI(
    title="TechShop AI Chatbot",
    description="Multi-agent chatbot for electronics e-commerce (laptop, phone, tablet)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files ─────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── WebSocket ───────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


# ─── Facebook Messenger webhook ───────────────────────────────────────────────
app.include_router(messenger_router, prefix="", tags=["Facebook Messenger"])


# ─── REST: Simulated product API ──────────────────────────────────────────────
@app.get("/api/products", tags=["Products"])
async def list_products(
    category: str = None,
    brand: str = None,
    max_price: int = None,
    min_price: int = None,
    use_case: str = None,
    q: str = None,
):
    results = search_products(
        category=category,
        brand=brand,
        max_price=max_price,
        min_price=min_price,
        use_case=use_case,
        keywords=[q] if q else [],
    )
    return {
        "total": len(results),
        "products": [
            {**p, "price_display": format_price(p["price"])}
            for p in results
        ],
    }


@app.get("/api/products/{product_id}", tags=["Products"])
async def get_product(product_id: str):
    from services.product_service import get_product_by_id
    p = get_product_by_id(product_id)
    if not p:
        return JSONResponse({"error": "Product not found"}, status_code=404)
    return {**p, "price_display": format_price(p["price"])}


# ─── REST: Session management ─────────────────────────────────────────────────
@app.get("/api/session/{session_id}", tags=["Session"])
async def session_state(session_id: str):
    return get_session_state(session_id)


@app.delete("/api/session/{session_id}", tags=["Session"])
async def end_session(session_id: str):
    clear_session(session_id)
    return {"status": "cleared"}


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "model": settings.MODEL,
        "products": len(PRODUCTS_DB),
        "fb_configured": bool(settings.FB_PAGE_ACCESS_TOKEN),
    }


# ─── Web chat UI ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
