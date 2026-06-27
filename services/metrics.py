"""
In-memory chatbot metrics store.
Resets on server restart — suitable for real-time dashboards.
For persistence, flush to DB periodically or replace with Redis counters.
"""
import time
import statistics
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class SessionMetrics:
    start_time: float = field(default_factory=time.time)
    turns: int = 0
    errors: int = 0
    fast_path_hits: int = 0
    intent_calls: int = 0          # LLM-based intent classifications
    intents: list = field(default_factory=list)
    latencies_ms: list = field(default_factory=list)
    ttft_ms: list = field(default_factory=list)
    order_placed: bool = False
    ended: bool = False
    end_time: float = 0.0
    oos_turns: int = 0             # out-of-scope messages this session
    injection_attempts: int = 0   # prompt injection attempts
    escalated: bool = False        # whether session was escalated to human
    escalation_reason: str = ""
    sentiments: list = field(default_factory=list)


class MetricsStore:
    def __init__(self):
        self._sessions: dict[str, SessionMetrics] = {}

    # ── Lifecycle ────────────────────────────────────────────────────────────
    def session_start(self, session_id: str):
        self._sessions[session_id] = SessionMetrics()

    def session_end(self, session_id: str):
        s = self._sessions.get(session_id)
        if s:
            s.ended = True
            s.end_time = time.time()

    def session_reconnect(self, session_id: str):
        s = self._sessions.get(session_id)
        if s:
            s.ended = False
            s.end_time = 0.0
        else:
            self._sessions[session_id] = SessionMetrics()

    # ── Per-turn recording ───────────────────────────────────────────────────
    def record_turn(
        self,
        session_id: str,
        *,
        intent: str = "",
        latency_ms: float = 0.0,
        ttft_ms: float | None = None,
        error: bool = False,
        order_placed: bool = False,
    ):
        s = self._get_or_create(session_id)
        s.turns += 1
        if error:
            s.errors += 1
        if intent:
            s.intents.append(intent)
        if latency_ms > 0:
            s.latencies_ms.append(latency_ms)
        if ttft_ms is not None and ttft_ms > 0:
            s.ttft_ms.append(ttft_ms)
        if order_placed:
            s.order_placed = True

    def record_fast_path(self, session_id: str):
        self._get_or_create(session_id).fast_path_hits += 1

    def record_intent_llm(self, session_id: str):
        self._get_or_create(session_id).intent_calls += 1

    def record_oos(self, session_id: str, oos_type: str, domain: str = ""):
        s = self._get_or_create(session_id)
        s.oos_turns += 1
        if oos_type == "injection":
            s.injection_attempts += 1

    def record_escalation(self, session_id: str, reason: str):
        s = self._get_or_create(session_id)
        if not s.escalated:
            s.escalated = True
            s.escalation_reason = reason

    def record_sentiment(self, session_id: str, sentiment: str):
        self._get_or_create(session_id).sentiments.append(sentiment)

    # ── Aggregation ──────────────────────────────────────────────────────────
    def get_active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if not s.ended)

    def summary(self, hours: int = 24) -> dict:
        cutoff = time.time() - hours * 3600
        sessions = [s for s in self._sessions.values() if s.start_time >= cutoff]
        total = len(sessions)

        if total == 0:
            return {
                "period_hours": hours,
                "total_sessions": 0,
                "active_sessions": self.get_active_count(),
                "orders": 0,
                "conversion_rate": 0.0,
                "avg_turns": 0.0,
                "total_turns": 0,
                "error_rate": 0.0,
                "fast_path_rate": 0.0,
                "latency_p50_ms": 0,
                "latency_p95_ms": 0,
                "latency_avg_ms": 0,
                "ttft_avg_ms": 0,
                "intent_distribution": {},
                "sessions_over_time": [],
                "oos_turns": 0,
                "oos_rate": 0.0,
                "injection_attempts": 0,
                "escalated_sessions": 0,
                "escalation_rate": 0.0,
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "positive_sentiment_rate": 0.0,
            }

        orders = sum(1 for s in sessions if s.order_placed)
        total_turns = sum(s.turns for s in sessions)
        total_errors = sum(s.errors for s in sessions)
        all_latencies = [l for s in sessions for l in s.latencies_ms]
        all_ttft = [t for s in sessions for t in s.ttft_ms]
        all_fast = sum(s.fast_path_hits for s in sessions)
        all_intent = sum(s.fast_path_hits + s.intent_calls for s in sessions)
        total_oos = sum(s.oos_turns for s in sessions)
        total_injections = sum(s.injection_attempts for s in sessions)
        total_escalated = sum(1 for s in sessions if s.escalated)

        intent_dist: dict[str, int] = defaultdict(int)
        for s in sessions:
            for intent in s.intents:
                intent_dist[intent] += 1

        all_sentiments = [s for sess in sessions for s in sess.sentiments]
        pos_count = all_sentiments.count('positive')
        neg_count = all_sentiments.count('negative')
        neutral_count = all_sentiments.count('neutral')
        total_sent = len(all_sentiments) or 1

        return {
            "period_hours": hours,
            "total_sessions": total,
            "active_sessions": self.get_active_count(),
            "orders": orders,
            "conversion_rate": round(orders / total * 100, 1),
            "avg_turns": round(total_turns / total, 1),
            "total_turns": total_turns,
            "error_rate": round(total_errors / max(total_turns, 1) * 100, 1),
            "fast_path_rate": round(all_fast / max(all_intent, 1) * 100, 1),
            "latency_p50_ms": int(_percentile(all_latencies, 50)),
            "latency_p95_ms": int(_percentile(all_latencies, 95)),
            "latency_avg_ms": int(sum(all_latencies) / max(len(all_latencies), 1)),
            "ttft_avg_ms": int(sum(all_ttft) / max(len(all_ttft), 1)),
            "intent_distribution": dict(
                sorted(intent_dist.items(), key=lambda x: -x[1])
            ),
            "sessions_over_time": _sessions_over_time(sessions, hours),
            "oos_turns": total_oos,
            "oos_rate": round(total_oos / max(total_turns, 1) * 100, 1),
            "injection_attempts": total_injections,
            "escalated_sessions": total_escalated,
            "escalation_rate": round(total_escalated / max(total, 1) * 100, 1),
            "sentiment_distribution": {"positive": pos_count, "negative": neg_count, "neutral": neutral_count},
            "positive_sentiment_rate": round(pos_count / total_sent * 100, 1),
        }

    def _get_or_create(self, session_id: str) -> SessionMetrics:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMetrics()
        return self._sessions[session_id]


def _percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = max(0, int(len(s) * p / 100) - 1)
    return s[min(idx, len(s) - 1)]


def _sessions_over_time(sessions: list[SessionMetrics], hours: int) -> list[dict]:
    """Bucket session counts into slots for a sparkline chart."""
    slots = min(hours, 24)
    bucket_secs = hours * 3600 / slots
    now = time.time()
    buckets: list[int] = [0] * slots

    for s in sessions:
        age = now - s.start_time
        idx = int(age / bucket_secs)
        slot = slots - 1 - min(idx, slots - 1)
        buckets[slot] += 1

    return [{"slot": i, "count": buckets[i]} for i in range(slots)]


metrics = MetricsStore()
