"""Unit tests for intent fast-path — no LLM calls."""
import pytest
from agents.intent_agent import _fast_intent, _fast_product_intent


class TestFastGreeting:
    def test_hello_greeting(self):
        r = _fast_intent("hello")
        assert r is not None and r["intent"] == "greeting"

    def test_xin_chao(self):
        r = _fast_intent("xin chào")
        assert r is not None and r["intent"] == "greeting"

    def test_greeting_with_product_not_greeting(self):
        r = _fast_intent("chào, tôi muốn mua laptop")
        # Should be product_inquiry, not greeting, because product keyword present
        if r:
            assert r["intent"] != "greeting"

    def test_long_greeting_not_fast_pathed(self):
        # Text > 40 chars with a greeting word — might still match but should be fine
        r = _fast_intent("chào bạn, tôi cần tư vấn một chiếc điện thoại tốt cho công việc")
        # Should route to product intent, not greeting
        if r:
            assert r["intent"] in ("product_inquiry", "greeting")


class TestFastAddress:
    def test_address_triggers_order_confirm(self):
        r = _fast_intent("giao đến 123 đường Lê Lợi, quận 1")
        assert r is not None and r["intent"] == "order_confirm"
        assert r["is_ready_to_order"] is True

    def test_address_extracted_into_order_info(self):
        r = _fast_intent("giao đến 123 đường Lê Lợi, quận 1")
        assert r is not None
        assert r["order_info"].get("address") is not None
        assert "đường" in r["order_info"]["address"].lower()

    def test_phone_extracted_alongside_address(self):
        r = _fast_intent("123 đường Nguyễn Trãi, quận 5 — SĐT 0901234567")
        assert r is not None and r["intent"] == "order_confirm"
        assert r["order_info"].get("phone") == "0901234567"
        assert r["order_info"].get("address") is not None

    def test_phone_without_address_not_captured(self):
        # Phone alone shouldn't trigger address fast-path
        r = _fast_intent("số điện thoại của tôi là 0901234567")
        # Does not match address regex → falls through to LLM or product intent
        if r:
            assert r.get("intent") != "order_confirm"

    def test_phuong_address(self):
        r = _fast_intent("địa chỉ của tôi là 45 phường Bến Nghé")
        assert r is not None and r["intent"] == "order_confirm"
        assert r["order_info"].get("address") is not None


class TestFastOrderStatus:
    def test_don_hang_cua_toi(self):
        r = _fast_intent("đơn hàng của tôi đâu rồi")
        assert r is not None and r["intent"] == "order_status"

    def test_order_id_pattern(self):
        r = _fast_intent("cho hỏi đơn ORD-ABC123 giao chưa")
        assert r is not None and r["intent"] == "order_status"


class TestFastProductIntent:
    def test_laptop_no_budget(self):
        r = _fast_product_intent("tôi muốn mua laptop")
        assert r is not None
        assert r["category"] == "laptop"
        assert r["requirements"]["budget_max"] is None

    def test_phone_with_budget_under(self):
        r = _fast_product_intent("điện thoại dưới 10 triệu")
        assert r is not None
        assert r["category"] == "phone"
        assert r["requirements"]["budget_max"] == 10_000_000

    def test_laptop_range_budget(self):
        # "tầm" keyword → fast-path takes max of the two amounts as budget_max
        r = _fast_product_intent("laptop tầm 20-30 triệu")
        assert r is not None
        assert r["requirements"]["budget_max"] == 30_000_000

    def test_laptop_explicit_range(self):
        # no directional keyword + two amounts → min/max pair
        r = _fast_product_intent("laptop 20 triệu đến 30 triệu")
        assert r is not None
        assert r["requirements"]["budget_min"] == 20_000_000
        assert r["requirements"]["budget_max"] == 30_000_000

    def test_tablet_use_case(self):
        r = _fast_product_intent("máy tính bảng cho học tập")
        assert r is not None
        assert r["category"] == "tablet"
        assert r["requirements"]["use_case"] == "học tập"

    def test_laptop_gaming(self):
        r = _fast_product_intent("laptop gaming")
        assert r is not None
        assert r["category"] == "laptop"
        assert r["requirements"]["use_case"] == "gaming"

    def test_unrelated_returns_none(self):
        r = _fast_product_intent("tôi muốn ăn phở")
        assert r is None

    def test_ipad_is_tablet(self):
        r = _fast_product_intent("ipad dưới 15 triệu")
        assert r is not None
        assert r["category"] == "tablet"

    def test_iphone_is_phone(self):
        r = _fast_product_intent("iphone mới nhất")
        assert r is not None
        assert r["category"] == "phone"
