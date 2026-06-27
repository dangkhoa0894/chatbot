"""
Lightweight BM25-style FAQ retrieval — no embeddings, no external deps.
Works by keyword overlap scoring over pre-indexed entries.
"""
import json
import re
import os
from functools import lru_cache


_FAQ_PATH = os.path.join(os.path.dirname(__file__), "../data/faq.json")


@lru_cache(maxsize=1)
def _load() -> list[dict]:
    try:
        with open(_FAQ_PATH, encoding="utf-8") as f:
            return json.load(f)["entries"]
    except Exception:
        return []


def _tokenize(text: str) -> set[str]:
    return set(re.split(r'[\s,./\\!?]+', text.lower())) - {
        '', 'và', 'của', 'cho', 'với', 'là', 'có', 'không', 'tôi', 'bạn'
    }


def retrieve(query: str, top_k: int = 2, min_score: float = 0.5) -> list[str]:
    """Return top-k relevant FAQ content strings for the query."""
    entries = _load()
    if not entries:
        return []

    q_tokens = _tokenize(query)
    q_lower = query.lower()
    scored = []

    for entry in entries:
        kw_set = set(entry.get("keywords", []))
        # Score: keyword token overlap + substring match bonus
        overlap = len(q_tokens & kw_set)
        bonus = sum(1 for kw in kw_set if kw in q_lower)
        score = overlap + bonus * 0.5
        if score >= min_score:
            scored.append((score, entry["title"], entry["content"]))

    scored.sort(reverse=True)
    return [f"[{title}]: {content}" for _, title, content in scored[:top_k]]
