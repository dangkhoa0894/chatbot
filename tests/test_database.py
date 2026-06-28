"""Unit tests for database layer — uses a temp SQLite file."""
import os
import tempfile
import pytest

# Point DB at a temp file before importing anything that reads DB_PATH
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_PATH"] = _tmp.name

from db.database import (
    init_db, create_order, get_orders,
    upsert_product, load_all_products, count_db_products,
    log_csat, get_csat_stats,
)


@pytest.fixture(autouse=True)
def fresh_db():
    """Re-initialise DB before each test."""
    import db.database as _db
    _db.DB_PATH = _tmp.name
    init_db()
    yield
    # clean slate: drop all rows between tests
    import sqlite3
    with sqlite3.connect(_tmp.name) as c:
        c.executescript("""
            DELETE FROM orders;
            DELETE FROM products;
            DELETE FROM token_logs;
            DELETE FROM csat_ratings;
            DELETE FROM escalations;
        """)


def _sample_product(pid="LP001", stock=10):
    return dict(
        id=pid, name="Test Laptop", brand="TestBrand", category="laptop",
        price=15_000_000, specs={}, highlight="", use_cases=[], pros=[], cons=[],
        stock=stock, rating=4.5, tags=[],
    )


# ── Orders ─────────────────────────────────────────────────────────────────────

class TestCreateOrder:
    def test_basic_insert(self):
        upsert_product(_sample_product())
        create_order(
            order_id="ORD-TEST01",
            session_id="sess-1",
            product_id="LP001",
            product_name="Test Laptop",
            price=15_000_000,
            address="123 Lê Lợi, Q1",
        )
        result = get_orders()
        assert result["total"] == 1
        row = result["rows"][0]
        assert row["id"] == "ORD-TEST01"
        assert row["product_id"] == "LP001"
        assert row["price"] == 15_000_000
        assert row["status"] == "confirmed"
        assert row["payment_method"] == "COD"

    def test_stock_decremented(self):
        upsert_product(_sample_product(stock=5))
        create_order(
            order_id="ORD-TEST02",
            session_id="sess-1",
            product_id="LP001",
            product_name="Test Laptop",
            price=15_000_000,
            address="456 Nguyễn Trãi",
        )
        products = load_all_products()
        lp = next(p for p in products if p["id"] == "LP001")
        assert lp["stock"] == 4

    def test_stock_floor_at_zero(self):
        upsert_product(_sample_product(stock=0))
        create_order(
            order_id="ORD-TEST03",
            session_id="sess-1",
            product_id="LP001",
            product_name="Test Laptop",
            price=15_000_000,
            address="789 Trần Hưng Đạo",
        )
        products = load_all_products()
        lp = next(p for p in products if p["id"] == "LP001")
        assert lp["stock"] == 0  # never goes negative

    def test_duplicate_order_id_ignored(self):
        upsert_product(_sample_product())
        kwargs = dict(
            order_id="ORD-DUP",
            session_id="sess-1",
            product_id="LP001",
            product_name="Test Laptop",
            price=15_000_000,
            address="1 Test St",
        )
        create_order(**kwargs)
        create_order(**kwargs)  # second call with same ID
        assert get_orders()["total"] == 1  # INSERT OR IGNORE

    def test_filter_by_session(self):
        upsert_product(_sample_product())
        create_order("ORD-S1A", "sess-A", "LP001", "Test Laptop", 15_000_000, "Addr 1")
        create_order("ORD-S1B", "sess-B", "LP001", "Test Laptop", 15_000_000, "Addr 2")
        result = get_orders(session_id="sess-A")
        assert result["total"] == 1
        assert result["rows"][0]["id"] == "ORD-S1A"

    def test_filter_by_status(self):
        upsert_product(_sample_product())
        create_order("ORD-CF", "sess-1", "LP001", "Test Laptop", 15_000_000, "Addr")
        assert get_orders(status="confirmed")["total"] == 1
        assert get_orders(status="shipped")["total"] == 0


# ── Products ───────────────────────────────────────────────────────────────────

class TestProducts:
    def test_upsert_and_load(self):
        upsert_product(_sample_product())
        products = load_all_products()
        assert any(p["id"] == "LP001" for p in products)

    def test_count_db_products(self):
        assert count_db_products() == 0
        upsert_product(_sample_product("LP001"))
        upsert_product(_sample_product("LP002"))
        assert count_db_products() == 2


# ── CSAT ───────────────────────────────────────────────────────────────────────

class TestCsat:
    def test_log_and_stats(self):
        log_csat("sess-1", 5, "great", "closing", 3)
        log_csat("sess-2", 1, "bad", "oos", 1)
        stats = get_csat_stats(days=30)
        assert stats["total"] == 2
        assert stats["avg_rating"] == 3.0
        assert stats["positive_rate"] == 50.0
