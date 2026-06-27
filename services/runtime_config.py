"""
In-memory runtime configuration — single source of truth for all tunable
parameters. Values take effect immediately across the entire process but
reset to env/defaults on server restart. Admin API reads/writes here.
"""
from config import settings

_ctx: dict = {
    "window": 8,           # messages kept verbatim in every LLM call
    "compress_at": 14,     # compress when len(messages) exceeds this
    "max_summary_chars": 600,  # cap on existing_summary fed back into summarizer
}

_llm_models: dict = {
    "intent":     settings.AGENT_MODELS.get("intent",  settings.MODEL),
    "closing":    settings.AGENT_MODELS.get("closing", settings.MODEL),
    "general":    settings.AGENT_MODELS.get("general", settings.MODEL),
    "summarizer": settings.MODEL,
}

_llm_tokens: dict = {
    "intent":     400,
    "closing":    800,
    "general":    500,
    "summarizer": 200,
}


def get_all() -> dict:
    return {
        "context": dict(_ctx),
        "llm": {
            "models": dict(_llm_models),
            "max_tokens": dict(_llm_tokens),
        },
    }


def get_ctx(key: str):
    return _ctx[key]


def get_model(agent: str) -> str:
    return _llm_models.get(agent, settings.MODEL)


def get_max_tokens(agent: str) -> int:
    return _llm_tokens.get(agent, 500)


def update(data: dict) -> None:
    if ctx_data := data.get("context"):
        for k, v in ctx_data.items():
            if k in _ctx:
                _ctx[k] = int(v)
    if llm_data := data.get("llm"):
        if models := llm_data.get("models"):
            for k, v in models.items():
                if k in _llm_models:
                    _llm_models[k] = str(v)
        if tokens := llm_data.get("max_tokens"):
            for k, v in tokens.items():
                if k in _llm_tokens:
                    _llm_tokens[k] = int(v)
