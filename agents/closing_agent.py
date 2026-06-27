import uuid
from models.state import ChatState
from services.product_service import format_price, format_products_compact
from services.llm_client import chat

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
→ Nếu THIẾU địa chỉ → hỏi địa chỉ giao hàng (bắt buộc)
→ Nếu ĐỦ thông tin (sản phẩm + địa chỉ) → xuất xác nhận đơn hàng:

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
    messages = state.get("messages", [])
    intent = state.get("intent", "general")
    products = state.get("recommended_products", [])
    order_info = state.get("order_info", {})
    is_ready = state.get("is_ready_to_order", False)
    stage = state.get("stage", "")

    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-4:]
    )

    has_address = bool(order_info.get("address"))

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
        f"[Địa chỉ]: {'có' if has_address else 'chưa có'}"
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

    is_confirming = intent == "order_confirm" and has_address and (selected or order_info.get("product_hint"))
    order_id = None
    if is_confirming:
        order_id = uuid.uuid4().hex[:6].upper()
        parts.append(f"[Mã đơn hàng mới]: #ORD-{order_id}")

    try:
        response = chat(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"Lịch sử hội thoại:\n{context}\n\n" + "\n\n".join(parts),
                },
            ],
            max_tokens=800,
            agent="closing",
            session_id=state.get("session_id", ""),
            stream=True,
        )
    except Exception as exc:
        response = f"Xin lỗi, có lỗi xảy ra. Vui lòng thử lại. ({exc})"

    new_state = {
        **state,
        "response": response,
        "stage": "confirmed" if is_confirming else "closing",
    }
    if selected:
        new_state["selected_product"] = selected
    if is_confirming and order_id:
        new_state["order_info"] = {
            **order_info,
            "order_id": f"ORD-{order_id}",
            "status": "confirmed",
        }

    return new_state


def general_node(state: ChatState) -> dict:
    messages = state.get("messages", [])
    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-4:]
    )
    try:
        response = chat(
            messages=[
                {"role": "system", "content": _GENERAL_SYSTEM},
                {"role": "user", "content": context},
            ],
            max_tokens=500,
            agent="general",
            session_id=state.get("session_id", ""),
            stream=True,
        )
    except Exception:
        response = (
            "Xin chào! Tôi là TechShop AI. Tôi có thể giúp bạn tìm "
            "laptop, điện thoại, máy tính bảng phù hợp. Bạn đang tìm kiếm gì? 😊"
        )

    return {**state, "response": response, "stage": "general"}
