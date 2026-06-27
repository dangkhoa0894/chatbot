"""
Tool execution node — runs after intent, before closing, when real-time
data is needed. Populates state["tools_data"] for closing_agent to read.
"""
from models.state import ChatState
from services.tools import check_inventory, get_order_status, get_active_promotions


def tools_node(state: ChatState) -> dict:
    intent = state.get("intent", "")
    tools_data: dict = {}

    if intent in ("order_confirm", "product_inquiry", "price_check"):
        # Check inventory for recommended products
        for p in state.get("recommended_products", [])[:3]:
            inv = check_inventory(p["id"])
            tools_data[f"inv_{p['id']}"] = inv
        # Check promotions for top product
        products = state.get("recommended_products", [])
        if products:
            promo = get_active_promotions(products[0]["id"])
            if promo:
                tools_data["promo"] = promo

    if intent == "order_status":
        order_info = state.get("order_info", {})
        order_id = order_info.get("order_id") or order_info.get("product_hint", "")
        if order_id:
            tools_data["order_status"] = get_order_status(order_id)

    return {**state, "tools_data": tools_data}
