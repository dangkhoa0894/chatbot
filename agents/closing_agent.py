import uuid
from models.state import ChatState
from services.product_service import format_price, format_products_compact
from services.llm_client import chat
from services.context_manager import build_messages
from services import runtime_config as _rc

_SYSTEM = """Bạn là chuyên gia tư vấn & chốt sale của TechShop AI (laptop, điện thoại, máy tính bảng).

Dựa trên ngữ cảnh, sản phẩm và thông tin đặt hàng, thực hiện đúng một trong các trường hợp:

**[A] Tư vấn sản phẩm lần đầu** (stage=search, chưa giới thiệu sản phẩm):
→ Giới thiệu 2-3 sản phẩm PHÙ HỢP NHẤT, giải thích ngắn TẠI SAO phù hợp với nhu cầu cụ thể
→ Dùng ✅ cho ưu điểm nổi bật, 🏆 cho sản phẩm đề xuất số 1
→ Kết bằng câu hỏi nhẹ dẫn tới đặt hàng

**[B] Khách hỏi thêm / phân vân** (đã có sản phẩm từ trước, stage=closing):
→ Xử lý objection, so sánh thêm hoặc gợi ý trả góp 0% nếu khách ngại giá
→ Tạo urgency nhẹ: "tồn kho có hạn", "đang được nhiều người quan tâm"

**[C] Khách xác nhận mua** (intent=order_confirm):
→ Kiểm tra [Thông tin đặt hàng] — nếu THIẾU BẤT KỲ trường nào trong 3 trường bắt buộc:
   • Địa chỉ giao hàng
   • Tên người nhận
   • Số điện thoại
  → Hỏi GỌN trong 1 tin nhắn tất cả các trường còn thiếu (không hỏi từng cái riêng lẻ)
→ Nếu ĐỦ CẢ 3 (địa chỉ + tên + SĐT) → xuất xác nhận đơn hàng:

🎉 ĐẶT HÀNG THÀNH CÔNG!
━━━━━━━━━━━━━━━━━━━━
📦 Sản phẩm: [tên đầy đủ]
💰 Giá: [giá]
📍 Giao đến: [địa chỉ]
👤 Người nhận: [tên hoặc "Chưa cung cấp"]
📞 SĐT: [số hoặc "Chưa cung cấp"]
🆔 Mã đơn: #[mã]
📅 Dự kiến giao: 2-3 ngày làm việc
💳 Thanh toán: COD khi nhận hàng
━━━━━━━━━━━━━━━━━━━━
Cảm ơn bạn đã tin tưởng TechShop AI! 🙏

**[D] Trạng thái đơn hàng** (intent=order_status):
→ Thông báo trạng thái từ [Trạng thái đơn hàng] trong context
→ Trấn an khách, dự kiến thời gian giao

Phong cách: Thân thiện, ngắn gọn, tiếng Việt tự nhiên, emoji vừa phải. Không dài dòng."""

_GENERAL_SYSTEM = """Bạn là nhân viên hỗ trợ khách hàng thân thiện của TechShop AI — cửa hàng điện tử bán laptop, điện thoại, máy tính bảng.

Nhiệm vụ:
- Chào hỏi nhiệt tình (nếu là lời chào)
- Trả lời câu hỏi về bảo hành, đổi trả, vận chuyển, thanh toán
- Giới thiệu các dòng sản phẩm có sẵn
- Luôn kết thúc bằng câu mời tư vấn sản phẩm hoặc hỏi nhu cầu của khách

Phong cách: Thân thiện, ngắn gọn, emoji phù hợp, tiếng Việt tự nhiên.
Thông tin: Bảo hành 12 tháng | Đổi trả 7 ngày | Ship miễn phí nội thành | Thanh toán COD/CK/trả góp 0%"""


def closing_node(state: ChatState) -> dict:
    intent = state.get("intent", "general")
    products = state.get("recommended_products", [])
    order_info = state.get("order_info", {})
    is_ready = state.get("is_ready_to_order", False)
    stage = state.get("stage", "")

    has_address = bool(order_info.get("address"))
    has_name = bool(order_info.get("name"))
    has_phone = bool(order_info.get("phone"))

    # Resolve the product the customer is interested in
    selected = state.get("selected_product")
    if not selected and order_info.get("product_hint") and products:
        hint = order_info["product_hint"].lower()
        selected = next(
            (p for p in products if hint in p["name"].lower() or hint in p["id"].lower()),
            products[0] if products else None,
        )
    elif not selected and products and intent == "order_confirm":
        selected = products[0]

    # Build compact situation block
    parts = [
        f"[Stage]: {stage} | [Intent]: {intent} | "
        f"[Sẵn sàng mua]: {'có' if is_ready else 'chưa'} | "
        f"[Địa chỉ]: {'✓' if has_address else 'THIẾU'} | "
        f"[Tên]: {'✓' if has_name else 'THIẾU'} | "
        f"[SĐT]: {'✓' if has_phone else 'THIẾU'}"
    ]

    if products:
        parts.append(f"[Sản phẩm phù hợp]:\n{format_products_compact(products[:3])}")

    if selected:
        parts.append(
            f"[Sản phẩm khách quan tâm]: {selected['name']} — {format_price(selected['price'])}"
        )

    if order_info:
        lines = [
            f"{label}: {order_info[k]}"
            for k, label in [
                ("product_hint", "SP muốn mua"), ("address", "Địa chỉ"),
                ("name", "Tên"), ("phone", "SĐT"),
            ]
            if order_info.get(k)
        ]
        if lines:
            parts.append("[Thông tin đặt hàng]:\n" + "\n".join(lines))

    # Inject real-time tools data
    tools_data = state.get("tools_data", {})

    inv_warnings = []
    for p in products[:3]:
        inv = tools_data.get(f"inv_{p['id']}")
        if inv and not inv.get("available"):
            inv_warnings.append(f"{p['name']}: HẾT HÀNG (nhập lại {inv.get('restock_eta', 'chưa rõ')})")
        elif inv and inv.get("stock", 99) <= 3:
            inv_warnings.append(f"{p['name']}: Sắp hết hàng (còn {inv['stock']} cái)")
    if inv_warnings:
        parts.append("[Cảnh báo tồn kho]:\n" + "\n".join(inv_warnings))

    promo = tools_data.get("promo")
    if promo:
        parts.append(f"[Khuyến mãi hiện tại]: {promo['label']} — {promo.get('ends_at', '')}")

    order_status = tools_data.get("order_status")
    if order_status:
        parts.append(
            f"[Trạng thái đơn hàng #{order_status.get('order_id', '')}]: "
            f"{order_status['label']} | Vị trí: {order_status['location']} | "
            f"ETA: {order_status.get('eta', '—')}"
        )

    # Sentiment tone hint
    sentiment = state.get("sentiment", "neutral")
    if sentiment == "negative":
        parts.append("[Gợi ý tone]: Khách đang không hài lòng — ưu tiên empathy, thừa nhận vấn đề trước khi tư vấn sản phẩm")
    elif sentiment == "positive":
        parts.append("[Gợi ý tone]: Khách đang tích cực — có thể upsell nhẹ hoặc reinforce lựa chọn")

    # Knowledge base context
    from services.knowledge_base import retrieve as _kb_retrieve
    last_user = next((m["content"] for m in reversed(state.get("messages", [])) if m["role"] == "user"), "")
    kb_chunks = _kb_retrieve(last_user)
    if kb_chunks:
        parts.append("[Thông tin chính sách liên quan]:\n" + "\n".join(kb_chunks))

    is_confirming = (
        intent == "order_confirm"
        and has_address and has_name and has_phone
        and (selected or order_info.get("product_hint"))
    )
    order_id = None
    if is_confirming:
        order_id = uuid.uuid4().hex[:6].upper()
        parts.append(f"[Mã đơn hàng mới]: #ORD-{order_id}")

    situation_block = "[Tình huống hiện tại]:\n" + "\n\n".join(parts)
    try:
        response = chat(
            messages=build_messages(state, _SYSTEM, extra_system=situation_block),
            max_tokens=_rc.get_max_tokens("closing"),
            agent="closing",
            session_id=state.get("session_id", ""),
            stream=True,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "closing_node failed session=%s: %s", state.get("session_id", ""), exc, exc_info=True
        )
        response = "Xin lỗi, có lỗi kỹ thuật xảy ra. Vui lòng thử lại sau ít phút."

    new_state = {
        **state,
        "response": response,
        "stage": "confirmed" if is_confirming else "closing",
    }
    if selected:
        new_state["selected_product"] = selected
    if is_confirming and order_id:
        full_order_id = f"ORD-{order_id}"
        new_state["order_info"] = {
            **order_info,
            "order_id": full_order_id,
            "status": "confirmed",
        }
        # Persist to DB and decrement stock
        try:
            from db.database import create_order as _create_order
            _create_order(
                order_id=full_order_id,
                session_id=state.get("session_id", ""),
                product_id=selected["id"] if selected else "",
                product_name=selected["name"] if selected else order_info.get("product_hint", ""),
                price=int(selected["price"]) if selected else 0,
                address=order_info.get("address", ""),
                customer_name=order_info.get("name", ""),
                customer_phone=order_info.get("phone", ""),
            )
        except Exception as _e:
            import logging as _log
            _log.getLogger(__name__).error("Failed to persist order %s: %s", full_order_id, _e)

    return new_state


def general_node(state: ChatState) -> dict:
    from services.knowledge_base import retrieve as _kb_retrieve
    last_user = next((m["content"] for m in reversed(state.get("messages", [])) if m["role"] == "user"), "")
    kb_chunks = _kb_retrieve(last_user)
    extra_system = ("[Thông tin chính sách liên quan]:\n" + "\n".join(kb_chunks)) if kb_chunks else None

    try:
        response = chat(
            messages=build_messages(state, _GENERAL_SYSTEM, extra_system=extra_system),
            max_tokens=_rc.get_max_tokens("general"),
            agent="general",
            session_id=state.get("session_id", ""),
            stream=True,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "general_node failed session=%s: %s", state.get("session_id", ""), exc, exc_info=True
        )
        response = "Xin chào! Tôi là TechShop AI, có thể giúp bạn tìm laptop, điện thoại, máy tính bảng. Bạn đang tìm gì?"

    return {**state, "response": response, "stage": "general"}
