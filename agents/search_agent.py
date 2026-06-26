from models.state import ChatState
from services.product_service import search_products, format_products_for_llm
from services.llm_client import chat

_SYSTEM = """Bạn là chuyên gia tư vấn sản phẩm điện tử (laptop, điện thoại, máy tính bảng).

Dựa trên yêu cầu của khách và danh sách sản phẩm có sẵn, hãy:
1. Gợi ý 2-3 sản phẩm PHÙ HỢP NHẤT — giải thích TẠI SAO mỗi sản phẩm phù hợp với nhu cầu cụ thể của khách
2. Nhấn mạnh điểm mạnh thiết thực (không chỉ liệt kê thông số kỹ thuật)
3. Nếu có sản phẩm nổi bật → đề xuất rõ ràng với lý do
4. Cuối cùng hỏi nhẹ nhàng để khách chọn hoặc cung cấp thêm thông tin

Phong cách: Thân thiện, chuyên nghiệp, dùng emoji phù hợp, tiếng Việt tự nhiên.
Định dạng: Dùng ký hiệu ✅ cho ưu điểm, 🏆 cho sản phẩm đề xuất."""


def search_node(state: ChatState) -> dict:
    messages = state.get("messages", [])
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
    if len(products) < 2 and category:
        products = search_products(category=category)
    if len(products) < 2:
        products = search_products()
    products = products[:6]

    context = "\n".join(
        f"{'Khách' if m['role'] == 'user' else 'Bot'}: {m['content']}"
        for m in messages[-4:]
    )

    req_lines = []
    if req.get("budget_max"):
        req_lines.append(f"Ngân sách tối đa: {req['budget_max']:,}đ")
    if req.get("budget_min"):
        req_lines.append(f"Ngân sách tối thiểu: {req['budget_min']:,}đ")
    if req.get("use_case"):
        req_lines.append(f"Mục đích: {req['use_case']}")
    if req.get("brand"):
        req_lines.append(f"Hãng ưa thích: {req['brand']}")
    if req.get("keywords"):
        req_lines.append(f"Từ khóa: {', '.join(req['keywords'])}")
    req_str = "\n".join(req_lines) or "Chưa có yêu cầu cụ thể"

    try:
        response = chat(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Lịch sử hội thoại gần đây:\n{context}\n\n"
                        f"Yêu cầu của khách:\n{req_str}\n\n"
                        f"Danh sách sản phẩm phù hợp:\n{format_products_for_llm(products)}\n\n"
                        "Hãy tư vấn sản phẩm phù hợp nhất."
                    ),
                },
            ],
            max_tokens=1200,
            agent="search",
            session_id=state.get("session_id", ""),
        )
    except Exception as exc:
        response = f"Xin lỗi, có lỗi khi tìm kiếm sản phẩm: {exc}"

    return {
        **state,
        "recommended_products": products,
        "stage": "search",
        "_search_draft": response,
    }
