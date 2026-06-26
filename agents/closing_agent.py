import uuid
from models.state import ChatState
from services.product_service import format_price, format_products_for_llm, get_product_by_id
from config import settings
import anthropic

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM = """Bạn là chuyên gia tư vấn & chốt sale sản phẩm điện tử, nhiệt tình và thân thiện.

Tùy tình huống hãy hành động phù hợp:

**[A] Vừa tìm được sản phẩm mới (có draft tư vấn từ search agent)**:
→ Trình bày sản phẩm gợi ý một cách hấp dẫn dựa trên draft
→ Tạo urgency nhẹ nhàng: "tồn kho có hạn", "đang được nhiều người quan tâm"
→ Hỏi khách có muốn đặt hàng hoặc tìm hiểu thêm không

**[B] Khách hỏi thêm / do dự về giá**:
→ Tư vấn thêm về sản phẩm, so sánh nếu cần
→ Xử lý objection: quá đắt → gợi ý trả góp 0% hoặc sản phẩm giá thấp hơn
→ Nhấn mạnh giá trị dài hạn

**[C] Khách đã đồng ý mua / cung cấp địa chỉ (order_confirm)**:
→ Xác nhận sản phẩm và địa chỉ với khách
→ Nếu THIẾU địa chỉ → hỏi địa chỉ giao hàng (bắt buộc)
→ Nếu ĐỦ thông tin (sản phẩm + địa chỉ) → tạo xác nhận đơn hàng:

```
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
```

Phong cách: Nhiệt tình, thân thiện, tiếng Việt tự nhiên. Dùng emoji vừa phải. Ngắn gọn, không dài dòng."""


def closing_node(state: ChatState) -> dict:
    messages = state.get("messages", [])
    intent = state.get("intent", "general")
    products = state.get("recommended_products", [])
    order_info = state.get("order_info", {})
    is_ready = state.get("is_ready_to_order", False)
    search_draft = state.get("_search_draft", "")

    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-6:]
    )

    # Determine situation
    has_address = bool(order_info.get("address"))
    has_product_hint = bool(order_info.get("product_hint"))

    # Figure out selected product
    selected = state.get("selected_product")
    if not selected and has_product_hint and products:
        hint = order_info["product_hint"].lower()
        for p in products:
            if hint in p["name"].lower() or hint in p["id"].lower():
                selected = p
                break
        if not selected:
            selected = products[0]  # default to top recommendation
    elif not selected and products:
        if intent == "order_confirm":
            selected = products[0]

    # Build context for LLM
    situation_parts = []

    if search_draft:
        situation_parts.append(f"[Draft tư vấn từ search agent]:\n{search_draft}")

    if products:
        situation_parts.append(f"[Sản phẩm được gợi ý]:\n{format_products_for_llm(products[:3])}")

    if selected:
        situation_parts.append(
            f"[Sản phẩm khách có vẻ quan tâm]: {selected['name']} — {format_price(selected['price'])}"
        )

    if order_info:
        order_lines = []
        if order_info.get("product_hint"):
            order_lines.append(f"Sản phẩm muốn mua: {order_info['product_hint']}")
        if order_info.get("address"):
            order_lines.append(f"Địa chỉ giao hàng: {order_info['address']}")
        if order_info.get("name"):
            order_lines.append(f"Tên người nhận: {order_info['name']}")
        if order_info.get("phone"):
            order_lines.append(f"Số điện thoại: {order_info['phone']}")
        if order_lines:
            situation_parts.append(f"[Thông tin đặt hàng đã có]:\n" + "\n".join(order_lines))

    situation_parts.append(f"[Intent hiện tại]: {intent}")
    situation_parts.append(f"[Khách sẵn sàng đặt hàng]: {'Có' if is_ready else 'Chưa rõ'}")
    situation_parts.append(f"[Có địa chỉ giao hàng]: {'Có' if has_address else 'Chưa'}")

    # Generate order ID if we're about to confirm
    order_id = None
    is_confirming = intent == "order_confirm" and has_address and (selected or has_product_hint)
    if is_confirming:
        order_id = uuid.uuid4().hex[:6].upper()
        situation_parts.append(f"[Mã đơn hàng mới]: #ORD-{order_id}")

    try:
        resp = _client.messages.create(
            model=settings.MODEL,
            max_tokens=1000,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Lịch sử hội thoại:\n{context}\n\n"
                    f"Thông tin tình huống:\n" + "\n\n".join(situation_parts)
                ),
            }],
        )
        response = resp.content[0].text
    except Exception as exc:
        response = f"Xin lỗi, có lỗi xảy ra. Vui lòng thử lại. ({exc})"

    new_state = {
        **state,
        "response": response,
        "stage": "confirmed" if is_confirming else "closing",
        "_search_draft": "",  # clear draft
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

    system = """Bạn là nhân viên hỗ trợ khách hàng thân thiện của TechShop AI — cửa hàng điện tử bán laptop, điện thoại, máy tính bảng.

Nhiệm vụ:
- Chào hỏi nhiệt tình (nếu là lời chào)
- Trả lời câu hỏi về bảo hành, đổi trả, vận chuyển, thanh toán
- Giới thiệu các dòng sản phẩm có sẵn
- Luôn kết thúc bằng câu mời tư vấn sản phẩm hoặc hỏi nhu cầu của khách

Phong cách: Thân thiện, ngắn gọn, dùng emoji phù hợp, tiếng Việt tự nhiên.

Thông tin cần thiết:
- Bảo hành: 12 tháng chính hãng
- Đổi trả: 7 ngày nếu lỗi sản xuất
- Vận chuyển: miễn phí nội thành, 2-3 ngày làm việc
- Thanh toán: COD, chuyển khoản, trả góp 0%"""

    try:
        resp = _client.messages.create(
            model=settings.MODEL,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": context}],
        )
        response = resp.content[0].text
    except Exception as exc:
        response = f"Xin chào! Tôi là TechShop AI. Tôi có thể giúp bạn tìm laptop, điện thoại, máy tính bảng phù hợp. Bạn đang tìm kiếm sản phẩm gì? 😊"

    return {**state, "response": response, "stage": "general"}
