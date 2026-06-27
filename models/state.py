from typing import TypedDict, Optional, List, Dict, Any


class ChatState(TypedDict):
    session_id: str
    messages: List[Dict[str, str]]        # [{"role": "user|assistant", "content": "..."}]
    context_summary: str                  # rolling LLM summary of compressed older turns
    intent: str                           # product_inquiry | order_confirm | price_check | support | greeting | general
    category: Optional[str]              # laptop | phone | tablet | None
    user_requirements: Dict[str, Any]    # extracted budget, use_case, brand, specs
    recommended_products: List[Dict[str, Any]]
    selected_product: Optional[Dict[str, Any]]
    order_info: Dict[str, Any]           # address, name, phone, product_hint
    is_ready_to_order: bool
    stage: str                           # intent | search | closing | general | confirmed
    response: str                        # final reply to send user
