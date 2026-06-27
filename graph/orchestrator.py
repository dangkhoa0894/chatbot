import asyncio
from langgraph.graph import StateGraph, END
from models.state import ChatState
from agents.intent_agent import intent_node
from agents.search_agent import search_node
from agents.closing_agent import closing_node, general_node
from services import session_store
from services.streaming import setup_streaming, clear_streaming


def _default_state(session_id: str) -> ChatState:
    return ChatState(
        session_id=session_id,
        messages=[],
        intent="",
        category=None,
        user_requirements={},
        recommended_products=[],
        selected_product=None,
        order_info={},
        is_ready_to_order=False,
        stage="intent",
        response="",
    )


def _route_after_intent(state: ChatState) -> str:
    intent = state.get("intent", "general")
    is_ready = state.get("is_ready_to_order", False)
    has_products = bool(state.get("recommended_products"))

    if intent in ("product_inquiry", "price_check"):
        return "closing" if has_products else "search"
    if intent == "order_confirm" or is_ready:
        return "closing"
    return "general"


def _build_graph():
    g = StateGraph(ChatState)
    g.add_node("intent", intent_node)
    g.add_node("search", search_node)
    g.add_node("closing", closing_node)
    g.add_node("general", general_node)
    g.set_entry_point("intent")
    g.add_conditional_edges(
        "intent", _route_after_intent,
        {"search": "search", "closing": "closing", "general": "general"},
    )
    g.add_edge("search", "closing")
    g.add_edge("closing", END)
    g.add_edge("general", END)
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
            # Push sentinel so the WebSocket streaming loop exits cleanly
            if token_queue is not None:
                asyncio.run_coroutine_threadsafe(token_queue.put(None), loop)

    result: ChatState = await loop.run_in_executor(None, _run_graph)

    response = result.get("response") or "Xin lỗi, tôi không hiểu. Bạn có thể nói lại không?"
    result["messages"] = messages + [{"role": "assistant", "content": response}]
    await session_store.save_session(session_id, result)
    return response


async def get_session_state(session_id: str) -> dict:
    return await session_store.get_session(session_id) or {}


async def clear_session(session_id: str) -> None:
    await session_store.delete_session(session_id)
