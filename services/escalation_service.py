"""
Escalation event emitter.
Delivers the event to a webhook (if configured) and always persists to DB.
Called synchronously from the graph executor thread — httpx sync client is safe here.
"""
import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


def emit_escalation_event(
    session_id: str,
    reason: str,
    messages: list,
    order_info: dict | None = None,
) -> None:
    info = order_info or {}
    payload = {
        "session_id": session_id,
        "reason": reason,
        "customer_name": info.get("name") or "",
        "customer_phone": info.get("phone") or "",
        "order_id": info.get("order_id") or "",
        "conversation_snapshot": messages[-10:],
    }

    _send_webhook(payload)
    logger.info("ESCALATION session=%s reason=%s", session_id, reason)

    from db.database import log_escalation
    try:
        log_escalation(
            session_id=session_id,
            reason=reason,
            customer_name=payload["customer_name"],
            customer_phone=payload["customer_phone"],
            order_id=payload["order_id"],
            snapshot=payload["conversation_snapshot"],
        )
    except Exception as exc:
        logger.warning("Failed to persist escalation: %s", exc)


def _send_webhook(payload: dict) -> None:
    url = getattr(settings, "ESCALATION_WEBHOOK_URL", "")
    if not url:
        return
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json=payload)
    except Exception as exc:
        logger.warning("Escalation webhook error: %s", exc)
