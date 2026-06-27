import asyncio
from langgraph.graph import StateGraph, END
from models.state import ChatState
from agents.intent_agent import intent_node
from agents.search_agent import search_node
from agents.closing_agent import closing_node, general_node
from agents.guard import guard_node, oos_node
from agents.escalation import escalation_node
from agents.tools_node import tools_node
from services import session_store
from services.streaming import setup_streaming, clear_streaming
from services.context_manager import should_compress, compress_history


def _default_state(session_id: str) -> ChatState:
    return ChatState(
        session_id=session_id,
        messages=[],
        context_summary="",
        intent="",
        category=None,
        user_requirements={},
        recommended_products=[],
        selected_product=None,
        order_info={},
        is_ready_to_order=False,
        stage="intent",
        response="",
        oos_count=0,
        oos_type="",
        oos_domain="",
        escalation_requested=False,
        escalation_reason="",
        stuck_count=0,
        csat_sent=False,
        tools_data={},
        sentiment="neutral",
    )


def _route_after_guard(state: ChatState) -> str:
    intent = state.get("intent", "")
    if intent == "escalation":
        return "escalation"
    if intent == "out_of_scope":
        return "oos"
    return "intent"


def _route_after_intent(state: ChatState) -> str:
    intent = state.get("intent", "general")
    is_ready = state.get("is_ready_to_order", False)

    if intent == "escalation":
        return "escalation"
    if intent == "out_of_scope":
        return "oos"
    if intent in ("product_inquiry", "price_check", "order_confirm", "order_status"):
        return "tools"
    if is_ready:
        return "tools"
    return "general"


def _route_after_tools(state: ChatState) -> str:
    intent = state.get("intent", "general")
    has_products = bool(state.get("recommended_products"))
    if intent in ("product_inquiry", "price_check") and not has_products:
        return "search"
    return "closing"


def _build_graph():
    g = StateGraph(ChatState)
    g.add_node("guard", guard_node)
    g.add_node("intent", intent_node)
    g.add_node("tools", tools_node)
    g.add_node("search", search_node)
    g.add_node("closing", closing_node)
    g.add_node("general", general_node)
    g.add_node("oos", oos_node)
    g.add_node("escalation", escalation_node)
    g.set_entry_point("guard")
    g.add_conditional_edges(
        "guard", _route_after_guard,
        {"intent": "intent", "oos": "oos", "escalation": "escalation"},
    )
    g.add_conditional_edges(
        "intent", _route_after_intent,
        {"tools": "tools", "general": "general",
         "oos": "oos", "escalation": "escalation"},
    )
    g.add_conditional_edges(
        "tools", _route_after_tools,
        {"search": "search", "closing": "closing"},
    )
    g.add_edge("search", "closing")
    g.add_edge("closing", END)
    g.add_edge("general", END)
    g.add_edge("oos", END)
    g.add_edge("escalation", END)
    return g.compile()


_graph = _build_graph()


async def process_message(
    session_id: str,
    user_message: str,
    token_queue: asyncio.Queue | None = None,
) -> str:
    state = await session_store.get_session(session_id)
    if state is None:
        state = _default_state(session_id)

    # Ensure fields added after initial deploy exist on older sessions
    if "context_summary" not in state:
        state["context_summary"] = ""
    if "oos_count" not in state:
        state["oos_count"] = 0
    if "oos_type" not in state:
        state["oos_type"] = ""
    if "oos_domain" not in state:
        state["oos_domain"] = ""
    if "escalation_requested" not in state:
        state["escalation_requested"] = False
    if "escalation_reason" not in state:
        state["escalation_reason"] = ""
    if "stuck_count" not in state:
        state["stuck_count"] = 0
    if "csat_sent" not in state:
        state["csat_sent"] = False
    if "tools_data" not in state:
        state["tools_data"] = {}
    if "sentiment" not in state:
        state["sentiment"] = "neutral"

    messages = list(state.get("messages", []))
    messages.append({"role": "user", "content": user_message})
    state["messages"] = messages

    loop = asyncio.get_event_loop()

    def _run_graph():
        if token_queue is not None:
            setup_streaming(token_queue, loop)
        try:
            return _graph.invoke(state)
        finally:
            clear_streaming()
            if token_queue is not None:
                asyncio.run_coroutine_threadsafe(token_queue.put(None), loop)

    result: ChatState = await loop.run_in_executor(None, _run_graph)

    response = result.get("response") or "Xin lỗi, tôi không hiểu. Bạn có thể nói lại không?"
    final_messages = messages + [{"role": "assistant", "content": response}]

    # Update stuck_count: consecutive turns with same unresolved intent signal a loop.
    _IGNORABLE = {"greeting", "general", "out_of_scope", "escalation", ""}
    new_intent = result.get("intent", "general")
    prev_intent = state.get("intent", "general")
    if new_intent == prev_intent and new_intent not in _IGNORABLE:
        result["stuck_count"] = state.get("stuck_count", 0) + 1
    else:
        result["stuck_count"] = 0

    # Save immediately so the client can send the next message without waiting
    # for compression. Compression runs as a best-effort background task.
    result["messages"] = final_messages
    await session_store.save_session(session_id, result)

    if should_compress(final_messages):
        asyncio.create_task(_bg_compress_and_save(session_id))

    return response


async def _bg_compress_and_save(session_id: str) -> None:
    """Compress conversation history in the background after a turn completes.

    Reads the latest session state so any concurrent turn that landed between
    the trigger and this execution is included in the compression window.
    Uses a double-read pattern: load → compress → re-read latest → patch only
    the context fields → save, so no agent state written by a concurrent turn
    is overwritten.
    """
    loop = asyncio.get_event_loop()
    try:
        state = await session_store.get_session(session_id)
        if state is None:
            return
        msgs = state.get("messages", [])
        if not should_compress(msgs):
            return  # A concurrent turn already compressed
        old_summary = state.get("context_summary", "")
        new_summary, trimmed = await loop.run_in_executor(
            None, compress_history, msgs, old_summary
        )
        # Re-read latest state to avoid overwriting fields written by a
        # concurrent turn that completed while we were compressing.
        latest = await session_store.get_session(session_id)
        if latest is None:
            return
        latest["context_summary"] = new_summary
        latest["messages"] = trimmed
        await session_store.save_session(session_id, latest)
    except Exception:
        pass  # Best-effort; next turn will retry if history still exceeds threshold


async def get_session_state(session_id: str) -> dict:
    return await session_store.get_session(session_id) or {}


async def clear_session(session_id: str) -> None:
    await session_store.delete_session(session_id)
