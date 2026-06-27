"""Input/output safety layer."""
import re

MAX_INPUT_CHARS = 1000

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?(?:previous|prior|above)\s+instructions?",
        r"forget\s+(?:everything|all)",
        r"new\s+instructions?\s*:",
        r"<\|(?:system|endoftext|im_start|im_end)\|>",
        r"disregard\s+(?:all|previous)",
        r"\[INST\]",
    ]
]

_ARTEFACT_RE = re.compile(r"<\|.*?\|>|\[/?INST\]|\[/?SYS\]", re.DOTALL)


def check_input(text: str) -> tuple[bool, str]:
    """Returns (is_safe, error_message)."""
    if not text or not text.strip():
        return False, "Tin nhắn trống."
    if len(text) > MAX_INPUT_CHARS:
        return False, f"Tin nhắn quá dài (tối đa {MAX_INPUT_CHARS} ký tự)."
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return False, "Yêu cầu không hợp lệ. Tôi chỉ hỗ trợ tư vấn mua sắm điện tử."
    return True, ""


def check_output(text: str) -> str:
    """Strip LLM artefacts from the response before sending to user."""
    return _ARTEFACT_RE.sub("", text).strip()
