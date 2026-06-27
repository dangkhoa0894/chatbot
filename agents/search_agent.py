from models.state import ChatState
from services.product_service import search_products


def search_node(state: ChatState) -> dict:
    """Pure Python product lookup — no LLM call.
    The closing_node handles recommendation text in the same pass."""
    req = state.get("user_requirements", {})
    category = state.get("category")

    products = search_products(
        category=category,
        max_price=req.get("budget_max"),
        min_price=req.get("budget_min"),
        brand=req.get("brand"),
        use_case=req.get("use_case"),
        keywords=req.get("keywords", []),
    )
    # Broaden search if too few results
    if len(products) < 2 and category:
        products = search_products(category=category)
    if len(products) < 2:
        products = search_products()

    return {
        **state,
        "recommended_products": products[:5],
        "stage": "search",
    }
