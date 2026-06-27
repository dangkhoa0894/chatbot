"""
Single entry point for all LLM calls.
Supports streaming (emits tokens via services.streaming) and per-agent model routing.
"""
import time
import logging

import openai
from openai import OpenAI
from config import settings
from db.database import log_token_usage

logger = logging.getLogger(__name__)

_client: OpenAI | None = None

# Circuit breaker state
_failure_count: int = 0
_circuit_open_until: float = 0.0

# Timeouts per agent type (seconds)
_CLOSING_AGENTS = {"closing"}
_TIMEOUT_CLOSING = 60.0
_TIMEOUT_DEFAULT = 30.0

# Retry config
_MAX_ATTEMPTS = 3
_RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds between attempt 1→2, 2→3, etc.
_RETRYABLE = (openai.APITimeoutError, openai.RateLimitError, openai.APIConnectionError)


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


def _check_circuit() -> None:
    """Raise immediately if the circuit breaker is open."""
    if _circuit_open_until and time.monotonic() < _circuit_open_until:
        raise RuntimeError("LLM unavailable: circuit open")


def _record_failure() -> None:
    global _failure_count, _circuit_open_until
    _failure_count += 1
    if _failure_count >= 5:
        _circuit_open_until = time.monotonic() + 30.0
        logger.error(
            "Circuit breaker opened after %d consecutive failures; "
            "will retry LLM in 30s",
            _failure_count,
        )


def _record_success() -> None:
    global _failure_count, _circuit_open_until
    _failure_count = 0
    _circuit_open_until = 0.0


def _do_stream(client: OpenAI, resolved_model: str, messages: list[dict],
               max_tokens: int, timeout: float) -> tuple[str, int, int, int]:
    """
    Attempt a single streaming call.
    Returns (full_text, prompt_tokens, completion_tokens, total_tokens).
    Raises on any exception so the caller can handle retries / fallback.
    """
    from services.streaming import emit_token  # local import avoids circular at module load

    full_text = ""
    prompt_tokens = completion_tokens = total_tokens = 0

    response = client.chat.completions.create(
        model=resolved_model,
        max_tokens=max_tokens,
        messages=messages,
        stream=True,
        timeout=timeout,
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

    return full_text, prompt_tokens, completion_tokens, total_tokens


def _do_non_stream(client: OpenAI, resolved_model: str, messages: list[dict],
                   max_tokens: int, timeout: float) -> tuple[str, int, int, int]:
    """
    Attempt a single non-streaming call.
    Returns (full_text, prompt_tokens, completion_tokens, total_tokens).
    Raises on any exception so the caller can handle retries.
    """
    resp = client.chat.completions.create(
        model=resolved_model,
        max_tokens=max_tokens,
        messages=messages,
        timeout=timeout,
    )
    full_text = (resp.choices[0].message.content or "").strip()
    prompt_tokens = completion_tokens = total_tokens = 0
    if resp.usage:
        prompt_tokens = resp.usage.prompt_tokens
        completion_tokens = resp.usage.completion_tokens
        total_tokens = resp.usage.total_tokens
    return full_text, prompt_tokens, completion_tokens, total_tokens


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
    Falls back to non-streaming silently if the streaming attempt fails.

    Resilience features:
    - Per-agent timeouts (60 s for closing agent, 30 s otherwise).
    - Retry with exponential back-off (up to 3 attempts) for transient errors.
    - Circuit breaker: opens for 30 s after 5 consecutive failures.
    """
    _check_circuit()

    resolved_model = _resolve_model(agent, model)
    client = _get_client()
    timeout = _TIMEOUT_CLOSING if agent in _CLOSING_AGENTS else _TIMEOUT_DEFAULT

    full_text = ""
    prompt_tokens = completion_tokens = total_tokens = 0
    last_exc: Exception | None = None

    # --- streaming path (single attempt; fall back to non-streaming on any error) ---
    if stream:
        try:
            full_text, prompt_tokens, completion_tokens, total_tokens = _do_stream(
                client, resolved_model, messages, max_tokens, timeout
            )
        except openai.AuthenticationError:
            # Non-retryable; propagate immediately without touching circuit state
            raise RuntimeError("LLM call failed")
        except Exception:
            # Fall back to non-streaming; do not count as a circuit-breaker failure yet
            stream = False
            full_text = ""

    # --- non-streaming path with retry + circuit breaker ---
    if not stream:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                full_text, prompt_tokens, completion_tokens, total_tokens = (
                    _do_non_stream(client, resolved_model, messages, max_tokens, timeout)
                )
                last_exc = None
                break  # success — exit retry loop
            except openai.AuthenticationError:
                # Non-retryable; propagate immediately without touching circuit state
                raise RuntimeError("LLM call failed")
            except _RETRYABLE as exc:
                last_exc = exc
                _record_failure()
                if attempt < _MAX_ATTEMPTS - 1:
                    delay = _RETRY_DELAYS[attempt]
                    logger.warning(
                        "LLM call failed (agent=%s, attempt=%d/%d, error=%s); "
                        "retrying in %.1fs",
                        agent, attempt + 1, _MAX_ATTEMPTS, type(exc).__name__, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d attempts (agent=%s, error=%s)",
                        _MAX_ATTEMPTS, agent, type(exc).__name__,
                    )
            except Exception as exc:
                last_exc = exc
                _record_failure()
                logger.error(
                    "LLM call failed with unexpected error (agent=%s, attempt=%d/%d, "
                    "error=%s)",
                    agent, attempt + 1, _MAX_ATTEMPTS, type(exc).__name__,
                )
                break  # non-retryable unexpected error — stop immediately

        if last_exc is not None:
            raise RuntimeError("LLM call failed")

    # --- success path ---
    _record_success()

    # Rough estimate when the provider omits usage in streaming mode
    if not total_tokens:
        completion_tokens = max(1, len(full_text) // 4)
        prompt_tokens = max(1, sum(len(m.get("content", "")) for m in messages) // 4)
        total_tokens = prompt_tokens + completion_tokens

    logger.debug(
        "LLM call succeeded (agent=%s, model=%s, approx_tokens=%d)",
        agent, resolved_model, total_tokens,
    )

    log_token_usage(
        agent=agent,
        model=resolved_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        session_id=session_id,
    )

    return full_text.strip()
