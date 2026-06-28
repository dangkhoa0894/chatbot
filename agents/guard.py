"""
Topic guard — runs BEFORE intent_node, no LLM call.

Check order (first match wins):
  1. Session already escalated  → route to escalation_node (show waiting msg)
  2. Explicit escalation request ("nhân viên", "human"...)
  3. Frustration / complaint keywords
  4. Conversation loop (stuck_count >= 2)
  5. Repeated OOS (oos_count >= 3)
  6. Off-topic domain patterns  → oos_node
  7. Prompt injection signatures → oos_node
  8. Pass through to intent_node
"""
import re
from models.state import ChatState
from services.metrics import metrics as _metrics

# ── Escalation triggers ───────────────────────────────────────────────────────
_EXPLICIT_ESCALATION_RE = re.compile(
    r'nhân viên|người thật|con người thật|gặp trực tiếp|gọi điện cho tôi'
    r'|hotline|quản lý|supervisor|human agent|\blive agent\b',
    re.I,
)

_FRUSTRATION_RE = re.compile(
    r'tức quá|bực quá|chán quá|thất vọng|lừa đảo|lừa tôi|tố cáo|báo cáo'
    r'|sản phẩm lỗi|hàng lỗi|giao nhầm|không hoạt động|hỏng rồi'
    r'|hoàn tiền ngay|trả hàng|đổi hàng|khiếu nại',
    re.I,
)

_FRUSTRATION_PUNCT_RE = re.compile(r'[!?]{4,}')

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


def _escalation_reason(text: str, state: ChatState) -> str | None:
    if state.get("escalation_requested"):
        return "already_escalated"
    if _EXPLICIT_ESCALATION_RE.search(text):
        return "explicit_request"
    if _FRUSTRATION_RE.search(text) or _FRUSTRATION_PUNCT_RE.search(text):
        return "frustration"
    if state.get("stuck_count", 0) >= 2:
        return "conversation_loop"
    return None


def guard_node(state: ChatState) -> dict:
    msgs = state.get("messages", [])
    last = next((m["content"] for m in reversed(msgs) if m["role"] == "user"), "")

    # ── Escalation check (highest priority) ──────────────────────────────────
    reason = _escalation_reason(last, state)
    if reason:
        return {
            **state,
            "intent": "escalation",
            "escalation_reason": reason,
            "stage": "guard",
        }

    # ── OOS + injection check ─────────────────────────────────────────────────
    detected = _detect(last)
    if not detected:
        # Reset stale intent so _route_after_guard always sends to intent_node,
        # even when the previous turn left intent="out_of_scope" or "escalation".
        return {**state, "intent": ""}

    oos_type, domain = detected
    oos_count = state.get("oos_count", 0) + 1
    _metrics.record_oos(state.get("session_id", ""), oos_type, domain)

    # Escalate after 3 OOS turns instead of continuing to deflect
    if oos_count >= 3:
        return {
            **state,
            "intent": "escalation",
            "escalation_reason": "repeated_oos",
            "oos_count": oos_count,
            "stage": "guard",
        }

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
