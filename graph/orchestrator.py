from langgraph.graph import StateGraph, END
from models.state import ChatState
from agents.intent_agent import intent_node
from agents.search_agent import search_node
from agents.closing_agent import closing_node, general_node

# ─── in-memory session store (swap with Redis for production) ───────────────
_sessions: dict[str, ChatState] = {}


def _get_session(session_id: str) -> ChatState:
    if session_id not in _sessions:
        _sessions[session_id] = ChatState(
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
    return dict(_sessions[session_id])


def _route_after_intent(state: ChatState) -> str:
    intent = state.get("intent", "general")
    is_ready = state.get("is_ready_to_order", False)
    has_products = bool(state.get("recommended_products"))

    if intent in ("product_inquiry", "price_check"):
        # If we already have recommended products from a previous turn, skip search
        return "closing" if has_products else "search"
    if intent == "order_confirm" or is_ready:
        return "closing"
    return "general"


# ─── build the LangGraph once at import time ────────────────────────────────
def _build_graph():
    g = StateGraph(ChatState)

    g.add_node("intent", intent_node)
    g.add_node("search", search_node)
    g.add_node("closing", closing_node)
    g.add_node("general", general_node)

    g.set_entry_point("intent")

    g.add_conditional_edges(
        "intent",
        _route_after_intent,
        {"search": "search", "closing": "closing", "general": "general"},
    )

    # After search always push to closing to present + soft-close
    g.add_edge("search", "closing")
    g.add_edge("closing", END)
    g.add_edge("general", END)

    return g.compile()


_graph = _build_graph()


# ─── public API ─────────────────────────────────────────────────────────────
async def process_message(session_id: str, user_message: str) -> str:
    """Process one user turn and return the assistant response."""
    state = _get_session(session_id)

    # Append incoming user message to conversation history
    messages = list(state["messages"])
    messages.append({"role": "user", "content": user_message})
    state["messages"] = messages

    # Run the multi-agent graph
    result: ChatState = _graph.invoke(state)

    response = result.get("response") or "Xin lỗi, tôi không hiểu. Bạn có thể nói lại không?"

    # Persist updated state (use result but keep our messages list)
    result_messages = list(messages)
    result_messages.append({"role": "assistant", "content": response})
    _sessions[session_id] = {**result, "messages": result_messages}

    return response


def get_session_state(session_id: str) -> ChatState:
    return _get_session(session_id)


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
