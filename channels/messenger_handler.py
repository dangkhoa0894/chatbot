import hashlib
import hmac
import json
import httpx
from fastapi import APIRouter, Request, Response, HTTPException, Query
from config import settings
from graph.orchestrator import process_message

router = APIRouter()

FB_API_URL = "https://graph.facebook.com/v19.0/me/messages"


# ─── Webhook verification ────────────────────────────────────────────────────
@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.FB_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


# ─── Receive messages ────────────────────────────────────────────────────────
@router.post("/webhook")
async def receive_webhook(request: Request):
    body_bytes = await request.body()

    # Signature verification (optional but recommended in production)
    if settings.FB_APP_SECRET:
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        if not _verify_signature(body_bytes, sig_header, settings.FB_APP_SECRET):
            raise HTTPException(status_code=403, detail="Invalid signature")

    body = json.loads(body_bytes)

    if body.get("object") != "page":
        return {"status": "ignored"}

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            await _handle_messaging_event(event)

    return {"status": "ok"}


async def _handle_messaging_event(event: dict):
    sender_id: str = event["sender"]["id"]

    if "message" in event:
        msg = event["message"]
        # Ignore echoes
        if msg.get("is_echo"):
            return
        text = msg.get("text", "").strip()
        if not text:
            await _send_text(sender_id, "Xin lỗi, tôi chỉ hỗ trợ tin nhắn văn bản. 📝")
            return
        await _process_and_reply(sender_id, text)

    elif "postback" in event:
        payload = event["postback"].get("payload", "")
        await _process_and_reply(sender_id, payload)


async def _process_and_reply(sender_id: str, user_text: str):
    try:
        response = await process_message(session_id=sender_id, user_message=user_text)
    except Exception as exc:
        response = f"Xin lỗi, có lỗi xảy ra. Vui lòng thử lại. ({exc})"

    # Facebook message limit is 2000 chars; split if needed
    for chunk in _split_message(response, max_len=1900):
        await _send_text(sender_id, chunk)


async def _send_text(recipient_id: str, text: str):
    if not settings.FB_PAGE_ACCESS_TOKEN:
        return  # silent no-op when token not configured

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                FB_API_URL,
                params={"access_token": settings.FB_PAGE_ACCESS_TOKEN},
                json=payload,
                timeout=10,
            )
        except Exception:
            pass  # log in production


def _verify_signature(body: bytes, signature: str, app_secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _split_message(text: str, max_len: int = 1900) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        parts.append(text[:max_len])
        text = text[max_len:]
    return parts
