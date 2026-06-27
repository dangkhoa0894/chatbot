"""
Single entry point for all LLM calls.
Supports streaming (emits tokens via services.streaming) and per-agent model routing.
"""
from openai import OpenAI
from config import settings
from db.database import log_token_usage

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.DEEPINFRA_API_KEY,
            base_url=settings.DEEPINFRA_BASE_URL,
        )
    return _client


def _resolve_model(agent: str, model: str | None) -> str:
    if model:
        return model
    from services import runtime_config as _rc
    return _rc.get_model(agent)


def chat(
    messages: list[dict],
    max_tokens: int,
    agent: str,
    session_id: str = "",
    model: str | None = None,
    stream: bool = False,
) -> str:
    """
    Call the LLM and return the response text.
    When stream=True, each token is emitted via services.streaming.emit_token()
    so the WebSocket handler can forward it to the browser in real-time.
    Falls back to non-streaming silently if the provider doesn't support it.
    """
    from services.streaming import emit_token  # local import avoids circular at module load

    resolved_model = _resolve_model(agent, model)
    client = _get_client()
    full_text = ""
    prompt_tokens = completion_tokens = total_tokens = 0

    if stream:
        try:
            response = client.chat.completions.create(
                model=resolved_model,
                max_tokens=max_tokens,
                messages=messages,
                stream=True,
            )
            for chunk in response:
                delta = (
                    chunk.choices[0].delta.content
                    if chunk.choices and chunk.choices[0].delta
                    else None
                )
                if delta:
                    emit_token(delta)
                    full_text += delta
                # Capture usage if the provider includes it in the final chunk
                usage = getattr(chunk, "usage", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                    total_tokens = getattr(usage, "total_tokens", 0) or 0
        except Exception:
            stream = False
            full_text = ""

    if not stream:
        resp = client.chat.completions.create(
            model=resolved_model,
            max_tokens=max_tokens,
            messages=messages,
        )
        full_text = (resp.choices[0].message.content or "").strip()
        if resp.usage:
            prompt_tokens = resp.usage.prompt_tokens
            completion_tokens = resp.usage.completion_tokens
            total_tokens = resp.usage.total_tokens

    # Rough estimate when the provider omits usage in streaming mode
    if not total_tokens:
        completion_tokens = max(1, len(full_text) // 4)
        prompt_tokens = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
        total_tokens = prompt_tokens + completion_tokens

    log_token_usage(
        agent=agent,
        model=resolved_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        session_id=session_id,
    )

    return full_text.strip()
