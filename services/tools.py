"""
Mock tool implementations — swap these for real API calls in production.
Each tool returns a structured dict; the closing_agent injects results
into its situation_block so the LLM can reason about them.
"""
from services.product_service import get_product_by_id


def check_inventory(product_id: str) -> dict:
    """Real impl: call WMS / ERP inventory API."""
    p = get_product_by_id(product_id)
    if not p:
        return {"available": False, "stock": 0, "restock_eta": None}
    stock = p.get("stock", 0)
    return {
        "available": stock > 0,
        "stock": stock,
        "restock_eta": "3-5 ngày làm việc" if stock == 0 else None,
    }


def get_order_status(order_id: str) -> dict:
    """Real impl: call shipping carrier API or OMS."""
    # Mock: return plausible data based on order_id hash
    _stage = hash(order_id) % 4
    stages = [
        {"status": "processing",       "label": "Đang xử lý",       "location": "Kho TechShop Hà Nội",    "eta": "1-2 ngày làm việc"},
        {"status": "shipped",          "label": "Đang vận chuyển",   "location": "Bưu cục quận Đống Đa",   "eta": "Hôm nay hoặc ngày mai"},
        {"status": "out_for_delivery", "label": "Đang giao",         "location": "Shipper đang trên đường", "eta": "Hôm nay"},
        {"status": "delivered",        "label": "Đã giao thành công","location": "Đã giao cho người nhận", "eta": None},
    ]
    return {"order_id": order_id, **stages[_stage]}


def get_active_promotions(product_id: str) -> dict | None:
    """Real impl: call promotion management system."""
    # Mock: 30% of products have a promo
    if hash(product_id) % 3 == 0:
        return {"discount_pct": 5, "label": "Giảm 5% khi thanh toán online", "ends_at": "Cuối tháng"}
    return None
