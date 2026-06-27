import json
import re
from models.state import ChatState
from services.llm_client import chat
from services.context_manager import build_messages
from services.metrics import metrics as _metrics

# ── Fast-path keyword rules (no LLM call needed) ───────────────────────────────
_GREETING_TRIGGERS = {'xin chào', 'chào', 'hi', 'hello', 'hey', 'alo', 'xin chao', 'chao', 'helo'}

_ADDRESS_RE = re.compile(
    r'\b\d+[\s,/\\]*.{0,30}(đường|phố|phường|quận|huyện|tỉnh|thành phố|tp\.?)\b',
    re.IGNORECASE,
)

_CAT_LAPTOP  = ['laptop', 'macbook', 'thinkpad', 'surface pro', 'máy tính xách tay']
_CAT_PHONE   = ['điện thoại', 'iphone', 'smartphone', 'android phone']
_CAT_TABLET  = ['máy tính bảng', 'ipad', 'galaxy tab', 'tablet']

_BUDGET_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:triệu|tr\b)', re.IGNORECASE)

_USE_CASE_MAP = {
    'lập trình': 'lập trình', 'coding': 'lập trình', 'code': 'lập trình',
    'gaming': 'gaming', 'game': 'gaming',
    'học tập': 'học tập', 'sinh viên': 'học tập',
    'văn phòng': 'văn phòng', 'làm việc': 'văn phòng',
    'chụp ảnh': 'chụp ảnh',
    'đồ họa': 'đồ họa', 'thiết kế': 'đồ họa', 'design': 'đồ họa',
    'vẽ': 'vẽ',
}


def _fast_product_intent(text: str) -> dict | None:
    t = text.lower()
    category = None
    for kw in _CAT_LAPTOP:
        if kw in t: category = 'laptop'; break
    if not category:
        for kw in _CAT_PHONE:
            if kw in t: category = 'phone'; break
    if not category:
        for kw in _CAT_TABLET:
            if kw in t: category = 'tablet'; break
    if not category:
        return None

    amounts = [float(m.replace(',', '.')) * 1_000_000 for m in _BUDGET_RE.findall(text)]
    budget_max = budget_min = None
    if amounts:
        if any(w in t for w in ('dưới', 'tối đa', 'không quá', 'tầm', 'khoảng')):
            budget_max = int(max(amounts))
        elif any(w in t for w in ('từ', 'trên', 'tối thiểu', 'ít nhất')):
            budget_min = int(min(amounts))
        elif len(amounts) >= 2:
            budget_min, budget_max = int(min(amounts)), int(max(amounts))
        else:
            budget_max = int(amounts[0])

    use_case, keywords = None, []
    for kw, uc in _USE_CASE_MAP.items():
        if kw in t:
            use_case = uc
            keywords.append(kw)
            break

    return {
        'intent': 'product_inquiry',
        'category': category,
        'requirements': {
            'budget_max': budget_max, 'budget_min': budget_min,
            'use_case': use_case, 'brand': None, 'keywords': keywords,
        },
        'order_info': {},
        'is_ready_to_order': False,
        'reasoning': 'fast-path product',
    }


def _fast_intent(text: str) -> dict | None:
    t = text.lower().strip()
    words = set(re.split(r'\W+', t))

    if words & _GREETING_TRIGGERS and len(text) < 40 and not any(
        k in t for k in ('laptop', 'điện thoại', 'phone', 'tablet', 'máy', 'giá', 'mua')
    ):
        return {'intent': 'greeting', 'category': None, 'requirements': {},
                'order_info': {}, 'is_ready_to_order': False, 'reasoning': 'fast-path'}

    if _ADDRESS_RE.search(text):
        return {'intent': 'order_confirm', 'category': None, 'requirements': {},
                'order_info': {}, 'is_ready_to_order': True, 'reasoning': 'fast-path address'}

    return _fast_product_intent(text)


_SYSTEM = """Bạn là AI phân tích ý định khách hàng cho cửa hàng điện tử bán laptop, điện thoại, máy tính bảng.

Phân tích TIN NHẮN CUỐI của khách dựa trên lịch sử hội thoại và thông tin đã ghi nhận.
Chỉ trả về JSON, không có text khác:

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

Quy tắc:
- "15 triệu" → 15000000, "dưới 20tr" → budget_max: 20000000
- "tầm 20-30 triệu" → min: 20000000, max: 30000000
- is_ready_to_order = true khi khách nói "mua", "đặt", "chốt", "lấy cái đó" hoặc cung cấp địa chỉ
- Nếu [Thông tin khách hàng đã ghi nhận] có category/budget, kế thừa nếu tin nhắn mới không thay đổi"""


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

    # Fast-path: skip LLM for obvious cases
    fast = _fast_intent(last_user)
    if fast:
        _metrics.record_fast_path(state.get("session_id", ""))
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

    # ── LLM path: use hierarchical context (entity memory + summary + recent turns) ──
    _metrics.record_intent_llm(state.get("session_id", ""))

    # build_messages gives us: system (with entities + summary) + recent turns
    # Append the analysis instruction to the last user message so the model
    # knows to output JSON rather than continue the conversation naturally.
    llm_msgs = build_messages(state, _SYSTEM)
    if llm_msgs and llm_msgs[-1]["role"] == "user":
        llm_msgs[-1] = {
            "role": "user",
            "content": llm_msgs[-1]["content"] + "\n\n[Phân tích tin nhắn trên và trả về JSON]",
        }

    try:
        raw = chat(
            messages=llm_msgs,
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
