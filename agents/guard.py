"""
Topic guard — runs BEFORE intent_node, no LLM call.

Two detection layers:
  1. Prompt injection signatures  → immediate block, separate metric
  2. Off-topic domain patterns    → polite deflection, escalates with oos_count

Design notes:
- Patterns are deliberately conservative to avoid false positives.
  A user saying "đầu tư một chiếc laptop tốt" should NOT trigger 'finance'.
- oos_count persists in session state so deflection text escalates naturally.
- After guard detects OOS it sets intent="out_of_scope"; the graph skips
  intent_node entirely and routes directly to oos_node.
"""
import re
from models.state import ChatState
from services.metrics import metrics as _metrics

# ── Off-topic domain patterns ─────────────────────────────────────────────────
# Keep patterns specific enough that tech-adjacent phrases don't trigger them.
_OOS_DOMAINS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'nấu ăn|công thức nấu|món ăn ngon|cách nấu|recipe', re.I), 'food'),
    (re.compile(r'thời tiết|dự báo thời tiết|nhiệt độ hôm nay', re.I), 'weather'),
    (re.compile(r'bóng đá|cầu thủ|bóng rổ|kết quả trận đấu|lịch thi đấu', re.I), 'sports'),
    (re.compile(r'chính trị|bầu cử|đảng phái|nghị sĩ|quốc hội', re.I), 'politics'),
    (re.compile(r'triệu chứng bệnh|chữa bệnh|uống thuốc gì|bác sĩ ơi', re.I), 'medical'),
    (re.compile(r'luật sư|tòa án|vụ kiện|điều luật', re.I), 'legal'),
    (re.compile(r'tình yêu|yêu đương|bạn trai|bạn gái|tán gái|tán trai', re.I), 'romance'),
    (re.compile(r'cổ phiếu|chứng khoán|forex|bitcoin|crypto|tiền điện tử', re.I), 'finance'),
    (re.compile(r'giải toán giùm|làm bài tập giùm|viết essay giùm|viết luận văn giúp', re.I), 'homework'),
]

# ── Prompt injection signatures ───────────────────────────────────────────────
_INJECTION_RE = re.compile(
    r'(ignore|forget|disregard|override).{0,30}(instruction|prompt|rule|above|previous)'
    r'|(you are now|act as|pretend to be|roleplay|jailbreak|\bDAN\b)'
    r'|(system\s*prompt|<\s*system\b)',
    re.I,
)

# ── Deflection templates (indexed by oos_count to feel natural) ───────────────
_DEFLECT = [
    "Câu hỏi này ngoài chuyên môn của mình — TechShop AI chuyên tư vấn laptop, điện thoại và máy tính bảng. Bạn đang tìm thiết bị gì không?",
    "Vấn đề này ngoài phạm vi TechShop AI rồi! Nhưng nếu bạn cần tư vấn laptop, điện thoại hay tablet thì mình sẵn sàng hỗ trợ nhé.",
    "Mình chỉ hỗ trợ về sản phẩm công nghệ tại TechShop AI. Bạn có muốn xem các sản phẩm đang bán không?",
]

_DEFLECT_PERSISTENT = (
    "Mình nhận thấy bạn hay hỏi các chủ đề ngoài lĩnh vực TechShop AI. "
    "Mình chỉ có thể tư vấn laptop, điện thoại, máy tính bảng và các dịch vụ liên quan (bảo hành, vận chuyển, thanh toán). "
    "Nếu bạn cần thiết bị công nghệ, mình rất vui được hỗ trợ!"
)

_INJECTION_REPLY = (
    "Mình chỉ hỗ trợ tư vấn sản phẩm công nghệ tại TechShop AI. "
    "Bạn cần tìm laptop, điện thoại hay máy tính bảng không?"
)


def _detect(text: str) -> tuple[str, str] | None:
    """Return (oos_type, domain) or None if in-scope."""
    if _INJECTION_RE.search(text):
        return ('injection', 'injection')
    for pattern, domain in _OOS_DOMAINS:
        if pattern.search(text):
            return ('off_topic', domain)
    return None


def guard_node(state: ChatState) -> dict:
    msgs = state.get("messages", [])
    last = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")

    detected = _detect(last)
    if not detected:
        return state  # pass through to intent_node

    oos_type, domain = detected
    oos_count = state.get("oos_count", 0) + 1
    _metrics.record_oos(state.get("session_id", ""), oos_type, domain)

    return {
        **state,
        "intent": "out_of_scope",
        "oos_count": oos_count,
        "oos_type": oos_type,
        "oos_domain": domain,
        "stage": "guard",
    }


def oos_node(state: ChatState) -> dict:
    oos_type = state.get("oos_type", "off_topic")
    oos_count = state.get("oos_count", 1)

    if oos_type == "injection":
        response = _INJECTION_REPLY
    elif oos_count >= 3:
        response = _DEFLECT_PERSISTENT
    else:
        response = _DEFLECT[(oos_count - 1) % len(_DEFLECT)]

    return {**state, "response": response, "stage": "oos"}
