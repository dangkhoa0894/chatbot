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

    from services import session_monitor
    session_monitor.flag_escalation(
        session_id,
        reason=reason,
        customer_name=payload["customer_name"],
        customer_phone=payload["customer_phone"],
    )


def _send_webhook(payload: dict, max_retries: int = 3) -> bool:
    url = getattr(settings, "ESCALATION_WEBHOOK_URL", "")
    if not url:
        return False
    import time
    last_exc = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                logger.info("Escalation webhook delivered on attempt %d", attempt + 1)
                return True
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                sleep_s = 2 ** attempt
                logger.warning("Escalation webhook attempt %d failed: %s, retrying in %ds", attempt + 1, exc, sleep_s)
                time.sleep(sleep_s)
    logger.error("Escalation webhook failed after %d attempts: %s — escalation persisted to DB only", max_retries, last_exc)
    return False
