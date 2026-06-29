from models.state import ChatState
from services.product_service import search_products


def search_node(state: ChatState) -> dict:
    """Pure Python product lookup — no LLM call.
    The closing_node handles recommendation text in the same pass."""
    req = state.get("user_requirements", {})
    category = state.get("category")
    sort_by_price = req.get("sort_by_price")

    products = search_products(
        category=category,
        max_price=req.get("budget_max"),
        min_price=req.get("budget_min"),
        brand=req.get("brand"),
        use_case=req.get("use_case"),
        keywords=req.get("keywords", []),
        sort_by_price=sort_by_price,
    )
    # Broaden search if too few results (preserve sort preference)
    if len(products) < 2 and category:
        products = search_products(category=category, sort_by_price=sort_by_price)
    if len(products) < 2:
        products = search_products(sort_by_price=sort_by_price)

    return {
        **state,
        "recommended_products": products[:5],
        "stage": "search",
    }
