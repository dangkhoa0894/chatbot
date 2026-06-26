"""
Single entry point for all LLM calls.
Tracks prompt/completion tokens to the DB automatically.
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


def chat(
    messages: list[dict],
    max_tokens: int,
    agent: str,
    session_id: str = "",
) -> str:
    """
    Call the LLM, log token usage, and return the response text.
    `agent` identifies which agent is making the call (for stats).
    """
    resp = _get_client().chat.completions.create(
        model=settings.MODEL,
        max_tokens=max_tokens,
        messages=messages,
    )

    if resp.usage:
        log_token_usage(
            agent=agent,
            model=settings.MODEL,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            total_tokens=resp.usage.total_tokens,
            session_id=session_id,
        )

    return (resp.choices[0].message.content or "").strip()
