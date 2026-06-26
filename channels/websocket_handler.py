import uuid
import json
from fastapi import WebSocket, WebSocketDisconnect
from graph.orchestrator import process_message, get_session_state, clear_session


class ConnectionManager:
    def __init__(self):
        self._active: dict[str, WebSocket] = {}  # session_id → ws

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        session_id = str(uuid.uuid4())
        self._active[session_id] = websocket
        return session_id

    def disconnect(self, session_id: str):
        self._active.pop(session_id, None)
        clear_session(session_id)

    async def send(self, session_id: str, data: dict):
        ws = self._active.get(session_id)
        if ws:
            await ws.send_text(json.dumps(data, ensure_ascii=False))


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    session_id = await manager.connect(websocket)

    # Send welcome
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

            # Typing indicator
            await manager.send(session_id, {"type": "typing", "is_typing": True})

            try:
                response = await process_message(session_id, user_text)
                state = get_session_state(session_id)
                await manager.send(session_id, {
                    "type": "message",
                    "role": "assistant",
                    "content": response,
                    "metadata": {
                        "intent": state.get("intent"),
                        "stage": state.get("stage"),
                        "products": _slim_products(state.get("recommended_products", [])),
                        "order": state.get("order_info") if state.get("stage") == "confirmed" else None,
                    },
                })
            except Exception as exc:
                await manager.send(session_id, {
                    "type": "error",
                    "content": f"Xin lỗi, có lỗi xảy ra. Vui lòng thử lại. ({exc})",
                })
            finally:
                await manager.send(session_id, {"type": "typing", "is_typing": False})

    except WebSocketDisconnect:
        manager.disconnect(session_id)


def _slim_products(products: list) -> list:
    """Return a lighter version of products for the frontend."""
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
