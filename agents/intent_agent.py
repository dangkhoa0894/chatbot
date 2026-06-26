import json
import re
from models.state import ChatState
from services.llm_client import chat

# ── Fast-path keyword rules (no LLM call needed) ───────────────────────────────
_GREETING_TRIGGERS = {'xin chào', 'chào', 'hi', 'hello', 'hey', 'alo', 'xin chao', 'chao', 'helo'}
_ADDRESS_RE = re.compile(
    r'\b\d+[\s,/\\]*.{0,30}(đường|phố|phường|quận|huyện|tỉnh|thành phố|tp\.?)\b',
    re.IGNORECASE,
)


def _fast_intent(text: str) -> dict | None:
    """Return a pre-classified result for obvious cases, else None to fall through to LLM."""
    t = text.lower().strip()
    words = set(re.split(r'\W+', t))
    # Pure greeting with no product keywords
    if words & _GREETING_TRIGGERS and len(text) < 40 and not any(
        k in t for k in ('laptop', 'điện thoại', 'phone', 'tablet', 'máy', 'giá', 'mua')
    ):
        return {'intent': 'greeting', 'category': None, 'requirements': {},
                'order_info': {}, 'is_ready_to_order': False, 'reasoning': 'fast-path'}
    # Message contains a clear street address → order confirmation
    if _ADDRESS_RE.search(text):
        return {'intent': 'order_confirm', 'category': None, 'requirements': {},
                'order_info': {}, 'is_ready_to_order': True, 'reasoning': 'fast-path address'}
    return None

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

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )

    # Try fast-path first to avoid an unnecessary LLM call
    fast = _fast_intent(last_user)
    if fast:
        existing_order = state.get("order_info", {})
        new_order = fast.get("order_info") or {}
        merged_order = {**existing_order, **{k: v for k, v in new_order.items() if v}}
        return {
            **state,
            "intent": fast["intent"],
            "category": fast.get("category") or state.get("category"),
            "user_requirements": fast.get("requirements", {}),
            "order_info": merged_order,
            "is_ready_to_order": fast.get("is_ready_to_order", False),
            "stage": "intent",
        }

    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-6:]
    )

    try:
        raw = chat(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Lịch sử hội thoại:\n{context}\n\n"
                        f"Phân tích tin nhắn cuối: \"{last_user}\""
                    ),
                },
            ],
            max_tokens=400,
            agent="intent",
            session_id=state.get("session_id", ""),
        )
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
