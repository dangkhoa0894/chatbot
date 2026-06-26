import json
import re
from models.state import ChatState
from config import settings
import anthropic

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

_SYSTEM = """Bạn là AI phân tích ý định khách hàng cho cửa hàng điện tử bán laptop, điện thoại, máy tính bảng.

Phân tích TIN NHẮN CUỐI của khách dựa trên lịch sử hội thoại. Chỉ trả về JSON, không có text khác:

{
  "intent": "product_inquiry" | "order_confirm" | "price_check" | "support" | "greeting" | "general",
  "category": "laptop" | "phone" | "tablet" | null,
  "requirements": {
    "budget_max": <số VND hoặc null>,
    "budget_min": <số VND hoặc null>,
    "use_case": "<mục đích hoặc null>",
    "brand": "<hãng hoặc null>",
    "keywords": ["<từ khóa>"],
    "specs": {}
  },
  "order_info": {
    "address": "<địa chỉ giao hàng hoặc null>",
    "name": "<tên người nhận hoặc null>",
    "phone": "<số điện thoại hoặc null>",
    "product_hint": "<tên/mã sản phẩm muốn mua hoặc null>"
  },
  "is_ready_to_order": <true/false>,
  "reasoning": "<giải thích ngắn>"
}

Quy tắc chuyển đổi:
- "15 triệu" → 15000000, "1.5tr" → 1500000, "dưới 20tr" → budget_max: 20000000
- "từ 10 triệu" → budget_min: 10000000, "tầm 20-30 triệu" → min: 20000000, max: 30000000
- is_ready_to_order = true khi khách nói "mua", "đặt", "chốt", "lấy cái đó" hoặc cung cấp địa chỉ
- intent = "order_confirm" khi có địa chỉ giao hàng hoặc xác nhận đặt hàng rõ ràng
- intent = "product_inquiry" khi hỏi về sản phẩm, tìm kiếm, so sánh
- intent = "greeting" khi chào hỏi, giới thiệu lần đầu"""


def intent_node(state: ChatState) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {
            **state,
            "intent": "greeting",
            "category": None,
            "user_requirements": {},
            "order_info": state.get("order_info", {}),
            "is_ready_to_order": False,
            "stage": "intent",
        }

    # Last 6 messages for context
    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-6:]
    )
    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    try:
        resp = _client.messages.create(
            model=settings.MODEL,
            max_tokens=700,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    f"Lịch sử hội thoại:\n{context}\n\n"
                    f"Phân tích tin nhắn cuối: \"{last_user}\""
                ),
            }],
        )
        raw = resp.content[0].text.strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(m.group() if m else raw)
    except Exception as exc:
        result = {
            "intent": "general",
            "category": None,
            "requirements": {},
            "order_info": {},
            "is_ready_to_order": False,
            "reasoning": f"parse error: {exc}",
        }

    # Merge order_info: keep previously collected fields, override with new non-null values
    existing_order = state.get("order_info", {})
    new_order = result.get("order_info", {}) or {}
    merged_order = {**existing_order, **{k: v for k, v in new_order.items() if v}}

    return {
        **state,
        "intent": result.get("intent", "general"),
        "category": result.get("category") or state.get("category"),
        "user_requirements": result.get("requirements", {}),
        "order_info": merged_order,
        "is_ready_to_order": result.get("is_ready_to_order", False),
        "stage": "intent",
    }
