import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "data/chatbot.db")


# ── Connection ─────────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


# ── Init ───────────────────────────────────────────────────────────────────────
def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS token_logs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                ts               TEXT    NOT NULL,
                agent            TEXT    NOT NULL,
                model            TEXT    NOT NULL,
                prompt_tokens    INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens     INTEGER DEFAULT 0,
                session_id       TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS products (
                id        TEXT PRIMARY KEY,
                name      TEXT    NOT NULL,
                brand     TEXT    NOT NULL,
                category  TEXT    NOT NULL,
                price     INTEGER NOT NULL,
                specs     TEXT    NOT NULL DEFAULT '{}',
                highlight TEXT    DEFAULT '',
                use_cases TEXT    DEFAULT '[]',
                pros      TEXT    DEFAULT '[]',
                cons      TEXT    DEFAULT '[]',
                stock     INTEGER DEFAULT 0,
                rating    REAL    DEFAULT 4.0,
                tags      TEXT    DEFAULT '[]',
                active    INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS escalations (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ts             TEXT    NOT NULL,
                session_id     TEXT    NOT NULL,
                reason         TEXT    NOT NULL,
                customer_name  TEXT    DEFAULT '',
                customer_phone TEXT    DEFAULT '',
                order_id       TEXT    DEFAULT '',
                snapshot       TEXT    DEFAULT '[]',
                resolved       INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_token_logs_ts      ON token_logs(ts);
            CREATE INDEX IF NOT EXISTS idx_token_logs_agent   ON token_logs(agent);
            CREATE INDEX IF NOT EXISTS idx_escalations_ts     ON escalations(ts);
            CREATE INDEX IF NOT EXISTS idx_escalations_reason ON escalations(reason);
        """)


# ── Token logging ──────────────────────────────────────────────────────────────
def log_token_usage(
    agent: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    session_id: str = "",
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO token_logs (ts, agent, model, prompt_tokens, completion_tokens, total_tokens, session_id)"
            " VALUES (?,?,?,?,?,?,?)",
            (ts, agent, model, prompt_tokens, completion_tokens, total_tokens, session_id),
        )


def get_token_stats(days: int = 7) -> dict:
    with _conn() as c:
        window = f"-{days} days"

        summary = dict(
            c.execute(
                "SELECT COALESCE(SUM(prompt_tokens),0) p, COALESCE(SUM(completion_tokens),0) co,"
                " COALESCE(SUM(total_tokens),0) t, COUNT(*) n"
                " FROM token_logs WHERE ts >= datetime('now', ?)",
                (window,),
            ).fetchone()
        )

        all_time = dict(
            c.execute(
                "SELECT COALESCE(SUM(total_tokens),0) t, COUNT(*) n FROM token_logs"
            ).fetchone()
        )

        by_agent = [
            dict(r) for r in c.execute(
                "SELECT agent, COALESCE(SUM(prompt_tokens),0) prompt_tokens,"
                " COALESCE(SUM(completion_tokens),0) completion_tokens,"
                " COALESCE(SUM(total_tokens),0) total_tokens, COUNT(*) requests"
                " FROM token_logs GROUP BY agent ORDER BY total_tokens DESC"
            ).fetchall()
        ]

        by_model = [
            dict(r) for r in c.execute(
                "SELECT model, COALESCE(SUM(prompt_tokens),0) prompt_tokens,"
                " COALESCE(SUM(completion_tokens),0) completion_tokens,"
                " COALESCE(SUM(total_tokens),0) total_tokens, COUNT(*) requests"
                " FROM token_logs GROUP BY model ORDER BY total_tokens DESC"
            ).fetchall()
        ]

        daily = [
            dict(r) for r in c.execute(
                "SELECT strftime('%Y-%m-%d', ts) day,"
                " COALESCE(SUM(prompt_tokens),0) prompt_tokens,"
                " COALESCE(SUM(completion_tokens),0) completion_tokens"
                " FROM token_logs WHERE ts >= datetime('now', ?)"
                " GROUP BY day ORDER BY day",
                (window,),
            ).fetchall()
        ]

    return {
        "summary": {
            "prompt_tokens": summary["p"],
            "completion_tokens": summary["co"],
            "total_tokens": summary["t"],
            "requests": summary["n"],
        },
        "all_time": {"total_tokens": all_time["t"], "requests": all_time["n"]},
        "by_agent": by_agent,
        "by_model": by_model,
        "daily": daily,
        "days": days,
    }


def get_token_logs(
    limit: int = 50,
    offset: int = 0,
    agent: str | None = None,
    model: str | None = None,
) -> dict:
    conditions, params = [], []
    if agent:
        conditions.append("agent = ?")
        params.append(agent)
    if model:
        conditions.append("model = ?")
        params.append(model)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with _conn() as c:
        total = c.execute(f"SELECT COUNT(*) FROM token_logs {where}", params).fetchone()[0]
        rows = c.execute(
            f"SELECT * FROM token_logs {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return {"total": total, "rows": [dict(r) for r in rows]}


def get_distinct_agents() -> list[str]:
    with _conn() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT agent FROM token_logs").fetchall()]


# ── Escalations ───────────────────────────────────────────────────────────────
def log_escalation(
    session_id: str,
    reason: str,
    customer_name: str = "",
    customer_phone: str = "",
    order_id: str = "",
    snapshot: list | None = None,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        c.execute(
            "INSERT INTO escalations (ts, session_id, reason, customer_name, customer_phone, order_id, snapshot)"
            " VALUES (?,?,?,?,?,?,?)",
            (ts, session_id, reason, customer_name, customer_phone, order_id,
             json.dumps(snapshot or [])),
        )


def get_escalations(limit: int = 50, offset: int = 0, resolved: int | None = None) -> dict:
    conditions, params = [], []
    if resolved is not None:
        conditions.append("resolved = ?")
        params.append(resolved)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    with _conn() as c:
        total = c.execute(f"SELECT COUNT(*) FROM escalations {where}", params).fetchone()[0]
        rows = c.execute(
            f"SELECT id,ts,session_id,reason,customer_name,customer_phone,order_id,resolved"
            f" FROM escalations {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    return {"total": total, "rows": [dict(r) for r in rows]}


def resolve_escalation(escalation_id: int) -> None:
    with _conn() as c:
        c.execute("UPDATE escalations SET resolved = 1 WHERE id = ?", (escalation_id,))


# ── Product CRUD ───────────────────────────────────────────────────────────────
def _to_db(p: dict) -> tuple:
    return (
        p["id"], p["name"], p["brand"], p["category"], int(p["price"]),
        json.dumps(p.get("specs", {})),
        p.get("highlight", ""),
        json.dumps(p.get("use_cases", [])),
        json.dumps(p.get("pros", [])),
        json.dumps(p.get("cons", [])),
        int(p.get("stock", 0)),
        float(p.get("rating", 4.0)),
        json.dumps(p.get("tags", [])),
    )


def _from_row(r) -> dict:
    p = dict(r)
    for key in ("specs", "use_cases", "pros", "cons", "tags"):
        p[key] = json.loads(p[key])
    p.pop("active", None)
    return p


def load_all_products() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM products WHERE active = 1 ORDER BY category, name").fetchall()
    return [_from_row(r) for r in rows]


def count_db_products() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM products WHERE active = 1").fetchone()[0]


def upsert_product(p: dict) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO products"
            " (id, name, brand, category, price, specs, highlight, use_cases, pros, cons, stock, rating, tags, active)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            _to_db(p),
        )


def delete_product(product_id: str) -> None:
    with _conn() as c:
        c.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))


def seed_products_if_empty(products: list[dict]) -> None:
    with _conn() as c:
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for p in products:
                c.execute(
                    "INSERT OR IGNORE INTO products"
                    " (id, name, brand, category, price, specs, highlight, use_cases, pros, cons, stock, rating, tags, active)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    _to_db(p),
                )
