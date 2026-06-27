import uuid
import asyncio
import json
import time
from fastapi import WebSocket, WebSocketDisconnect
from graph.orchestrator import process_message, get_session_state, clear_session
from services.rate_limiter import rate_limiter
from services.metrics import metrics
from middleware.guardrails import check_input, check_output


class ConnectionManager:
    def __init__(self):
        self._active: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self._active[session_id] = websocket
        return session_id

    async def disconnect(self, session_id: str):
        self._active.pop(session_id, None)
        metrics.session_end(session_id)
        await clear_session(session_id)

    async def send(self, session_id: str, data: dict):
        ws = self._active.get(session_id)
        if ws:
            await ws.send_text(json.dumps(data, ensure_ascii=False))


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    session_id = await manager.connect(websocket)
    metrics.session_start(session_id)

    await manager.send(session_id, {
        "type": "connected",
        "session_id": session_id,
        "message": (
            "👋 Xin chào! Tôi là TechShop AI — trợ lý tư vấn mua sắm điện tử.\n"
            "Tôi có thể giúp bạn tìm laptop, điện thoại, máy tính bảng phù hợp nhất.\n\n"
            "Bạn đang tìm kiếm sản phẩm gì? 😊"
        ),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                user_text = payload.get("message", "").strip()
            except json.JSONDecodeError:
                user_text = raw.strip()

            if not user_text:
                continue

            # ── Rate limiting ────────────────────────────────────────────────
            if not rate_limiter.is_allowed(session_id):
                await manager.send(session_id, {
                    "type": "error",
                    "content": "Bạn gửi tin nhắn quá nhanh. Vui lòng chờ một chút.",
                })
                continue

            # ── Guardrails: input check ──────────────────────────────────────
            is_safe, reason = check_input(user_text)
            if not is_safe:
                await manager.send(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": reason,
                    "metadata": {},
                })
                continue

            # ── Typing indicator ─────────────────────────────────────────────
            await manager.send(session_id, {"type": "typing", "is_typing": True})

            token_queue: asyncio.Queue = asyncio.Queue()
            turn_t0 = time.perf_counter()
            ttft_ms: float | None = None
            first_token = True
            error_occurred = False

            try:
                # Start graph processing; tokens stream to browser in parallel
                process_task = asyncio.create_task(
                    process_message(session_id, user_text, token_queue)
                )

                # Forward tokens to client until sentinel (None)
                while True:
                    try:
                        token = await asyncio.wait_for(token_queue.get(), timeout=60.0)
                    except asyncio.TimeoutError:
                        break
                    if token is None:
                        break
                    if first_token:
                        ttft_ms = (time.perf_counter() - turn_t0) * 1000
                        first_token = False
                    await manager.send(session_id, {"type": "token", "delta": token})

                response = await process_task
                latency_ms = (time.perf_counter() - turn_t0) * 1000

                # ── Guardrails: output check ─────────────────────────────────
                response = check_output(response)

                state = await get_session_state(session_id)
                order_confirmed = state.get("stage") == "confirmed"

                metrics.record_turn(
                    session_id,
                    intent=state.get("intent", ""),
                    latency_ms=latency_ms,
                    ttft_ms=ttft_ms,
                    error=False,
                    order_placed=order_confirmed,
                )

                await manager.send(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": response,
                    "metadata": {
                        "intent": state.get("intent"),
                        "stage": state.get("stage"),
                        "products": _slim_products(state.get("recommended_products", [])),
                        "order": state.get("order_info") if order_confirmed else None,
                    },
                })

            except Exception:
                error_occurred = True
                metrics.record_turn(session_id, error=True)
                await manager.send(session_id, {
                    "type": "error",
                    "content": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
                })
            finally:
                await manager.send(session_id, {"type": "typing", "is_typing": False})

    except WebSocketDisconnect:
        await manager.disconnect(session_id)


def _slim_products(products: list) -> list:
    slim = []
    for p in products[:3]:
        slim.append({
            "id": p["id"],
            "name": p["name"],
            "brand": p["brand"],
            "price": p["price"],
            "price_display": f"{p['price']:,}đ".replace(",", "."),
            "highlight": p.get("highlight", ""),
            "rating": p.get("rating", 0),
            "stock": p.get("stock", 0),
        })
    return slim
