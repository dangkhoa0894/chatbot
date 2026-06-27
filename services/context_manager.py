"""
Hierarchical context management for multi-turn conversations.

Three-layer architecture:
  1. Recent raw turns  — last WINDOW messages, verbatim, native role/content format
  2. Rolling summary   — LLM-compressed summary of older turns (triggered at COMPRESS_AT)
  3. Entity memory     — structured facts (budget, category, etc.) that persist across all turns

This replaces ad-hoc messages[-4:] slicing scattered across agents with a single,
consistent interface used by every agent that calls an LLM.
"""

WINDOW = 8        # recent messages kept verbatim
COMPRESS_AT = 14  # trigger rolling compression above this count

_SUMMARY_SYSTEM = (
    "Bạn là AI tóm tắt hội thoại bán hàng điện tử. "
    "Tóm tắt ngắn gọn (3-5 câu) những điểm quan trọng từ đoạn hội thoại, tập trung vào:\n"
    "- Nhu cầu / yêu cầu khách hàng đã nêu\n"
    "- Sản phẩm đã được đề cập hoặc giới thiệu\n"
    "- Quyết định, phản hồi, hoặc objection quan trọng\n"
    "- Thông tin đặt hàng nếu có\n"
    "Chỉ viết sự kiện và thông tin quan trọng, không chào hỏi."
)


def should_compress(messages: list) -> bool:
    return len(messages) > COMPRESS_AT


def compress_history(messages: list, existing_summary: str = "") -> tuple[str, list]:
    """
    Summarize old messages into a compact summary, keep only recent ones.
    Returns (new_summary, trimmed_messages_list).
    Called from orchestrator via run_in_executor (sync-safe).
    On LLM failure: returns (existing_summary, original_messages) unchanged.
    """
    from services.llm_client import chat

    to_summarize = messages[:-WINDOW]
    keep = messages[-WINDOW:]

    history_text = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in to_summarize
    )

    prefix = f"[Tóm tắt trước đó]:\n{existing_summary}\n\n" if existing_summary else ""

    try:
        new_summary = chat(
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM},
                {"role": "user", "content": f"{prefix}[Hội thoại cần tóm tắt]:\n{history_text}"},
            ],
            max_tokens=200,
            agent="summarizer",
            stream=False,
        )
        return new_summary.strip(), keep
    except Exception:
        return existing_summary, messages


def build_messages(state: dict, system_prompt: str, *, extra_system: str = "") -> list[dict]:
    """
    Build a properly formatted multi-turn messages array for an LLM call.

    Layout:
      [system]  base system_prompt
                + entity memory (structured facts from state)
                + rolling summary (compressed older turns)
                + extra_system (agent-specific situational context)
      [user]    turn 1
      [asst]    turn 1
      ...
      [user]    latest message  ← model generates response to this

    The model sees conversation in its native role/content format rather than
    as a concatenated string — identical to how ChatGPT / Claude are called.
    """
    messages = state.get("messages", [])
    summary = state.get("context_summary", "")

    # ── Assemble enriched system prompt ──────────────────────────────────────
    system_parts = [system_prompt.rstrip()]

    entity_block = _entity_block(state)
    if entity_block:
        system_parts.append("\n[Thông tin khách hàng đã ghi nhận]:\n" + entity_block)

    if summary:
        system_parts.append(f"\n[Tóm tắt hội thoại trước]:\n{summary}")

    if extra_system:
        system_parts.append("\n" + extra_system.strip())

    result: list[dict] = [{"role": "system", "content": "\n".join(system_parts)}]

    # ── Append recent turns in native multi-turn format ───────────────────────
    for msg in messages[-WINDOW:]:
        role = msg["role"]          # "user" or "assistant"
        result.append({"role": role, "content": msg["content"]})

    return result


def _entity_block(state: dict) -> str:
    """Render session entities as a compact bullet list."""
    lines = []
    req = state.get("user_requirements", {}) or {}

    if state.get("category"):
        lines.append(f"• Danh mục: {state['category']}")
    if req.get("budget_max"):
        lines.append(f"• Ngân sách tối đa: {req['budget_max']:,}đ")
    if req.get("budget_min"):
        lines.append(f"• Ngân sách tối thiểu: {req['budget_min']:,}đ")
    if req.get("use_case"):
        lines.append(f"• Mục đích: {req['use_case']}")
    if req.get("brand"):
        lines.append(f"• Hãng ưa thích: {req['brand']}")
    if state.get("selected_product"):
        sp = state["selected_product"]
        price = sp.get("price", 0)
        lines.append(f"• Sản phẩm quan tâm: {sp.get('name', '')} — {price:,}đ")

    order = state.get("order_info", {}) or {}
    if order.get("name"):
        lines.append(f"• Người nhận: {order['name']}")
    if order.get("phone"):
        lines.append(f"• SĐT: {order['phone']}")
    if order.get("address"):
        lines.append(f"• Địa chỉ giao hàng: {order['address']}")

    return "\n".join(lines)
