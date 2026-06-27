"""
Escalation node — fires when the guard routes intent="escalation".
Generates an empathetic handoff response, emits an event, and locks
the session into "waiting for agent" mode for all subsequent turns.
"""
from models.state import ChatState
from services.escalation_service import emit_escalation_event
from services.metrics import metrics as _metrics

_RESPONSES = {
    "explicit_request": (
        "Mình hiểu bạn muốn được hỗ trợ trực tiếp từ nhân viên. "
        "Mình đang kết nối bạn với đội ngũ TechShop AI ngay bây giờ. "
        "Vui lòng giữ máy trong giây lát, nhân viên sẽ liên hệ bạn sớm nhất! 📞"
    ),
    "frustration": (
        "Mình xin lỗi vì trải nghiệm chưa tốt. "
        "Để giải quyết vấn đề nhanh nhất, mình đang chuyển bạn đến nhân viên hỗ trợ TechShop AI. "
        "Bạn sẽ được liên hệ trong thời gian sớm nhất! 🙏"
    ),
    "conversation_loop": (
        "Có vẻ mình chưa hỗ trợ đúng điều bạn cần. "
        "Mình sẽ kết nối bạn với nhân viên TechShop AI để được tư vấn trực tiếp. "
        "Cảm ơn bạn đã kiên nhẫn! 🙏"
    ),
    "repeated_oos": (
        "Mình nhận thấy câu hỏi của bạn nằm ngoài phạm vi TechShop AI. "
        "Để đảm bảo bạn được hỗ trợ đúng nhất, mình kết nối bạn với nhân viên nhé! 📞"
    ),
    "already_escalated": (
        "Bạn đã được kết nối với đội hỗ trợ TechShop AI. "
        "Nhân viên sẽ liên hệ bạn sớm nhất có thể — vui lòng giữ máy! 🙏"
    ),
}

_DEFAULT_RESPONSE = (
    "Mình đang kết nối bạn với nhân viên hỗ trợ TechShop AI. "
    "Nhân viên sẽ liên hệ bạn sớm nhất! 📞"
)


def escalation_node(state: ChatState) -> dict:
    reason = state.get("escalation_reason", "")
    already = reason == "already_escalated"

    if not already:
        emit_escalation_event(
            session_id=state.get("session_id", ""),
            reason=reason,
            messages=state.get("messages", []),
            order_info=state.get("order_info", {}),
        )
        _metrics.record_escalation(state.get("session_id", ""), reason)

    response = _RESPONSES.get(reason, _DEFAULT_RESPONSE)

    return {
        **state,
        "response": response,
        "stage": "escalated",
        "escalation_requested": True,
    }
