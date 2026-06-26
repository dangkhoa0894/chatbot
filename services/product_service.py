from typing import Optional, List

# ── Seed data (used to bootstrap the DB on first run) ─────────────────────────
PRODUCTS_DB: List[dict] = [
    # ──────────────────── LAPTOPS ────────────────────
    {
        "id": "LP001",
        "name": "MacBook Pro 14\" M3 Pro",
        "brand": "Apple",
        "category": "laptop",
        "price": 55990000,
        "specs": {
            "cpu": "Apple M3 Pro 11-core",
            "ram": "18GB Unified Memory",
            "storage": "512GB SSD",
            "display": "14.2\" Liquid Retina XDR, 120Hz ProMotion",
            "gpu": "14-core GPU",
            "battery": "22 giờ",
            "weight": "1.61kg",
            "os": "macOS Sonoma",
            "ports": "3x Thunderbolt 4, HDMI 2.1, SD Card, MagSafe 3",
        },
        "highlight": "Hiệu năng đỉnh cao cho lập trình viên & nhà sáng tạo",
        "use_cases": ["lập trình", "đồ họa", "video editing", "thiết kế", "sáng tạo"],
        "pros": ["Pin 22 giờ", "Màn hình Liquid XDR cực đẹp", "Hiệu năng vượt trội", "Build quality cao cấp"],
        "cons": ["Giá cao", "Không hỗ trợ game Windows", "RAM không nâng cấp được"],
        "stock": 12,
        "rating": 4.9,
        "tags": ["pin lâu", "đồ họa", "lập trình", "cao cấp", "macOS", "mỏng nhẹ"],
    },
    {
        "id": "LP002",
        "name": "Dell XPS 15 9530",
        "brand": "Dell",
        "category": "laptop",
        "price": 42990000,
        "specs": {
            "cpu": "Intel Core i7-13700H (14-core)",
            "ram": "32GB DDR5",
            "storage": "1TB NVMe SSD",
            "display": "15.6\" OLED 3.5K, 60Hz, 100% DCI-P3",
            "gpu": "NVIDIA RTX 4060 8GB",
            "battery": "13 giờ",
            "weight": "1.86kg",
            "os": "Windows 11 Home",
            "ports": "2x Thunderbolt 4, USB-A, SD Card, 3.5mm",
        },
        "highlight": "Laptop Windows cao cấp nhất cho đồ họa và lập trình",
        "use_cases": ["lập trình", "đồ họa", "video editing", "thiết kế", "game nhẹ"],
        "pros": ["Màn hình OLED đẹp", "RAM 32GB", "RTX 4060", "Thiết kế sang trọng"],
        "cons": ["Pin trung bình", "Giá cao", "Tản nhiệt hơi ồn khi tải nặng"],
        "stock": 8,
        "rating": 4.7,
        "tags": ["đồ họa", "lập trình", "Windows", "OLED", "RTX", "cao cấp"],
    },
    {
        "id": "LP003",
        "name": "Lenovo ThinkPad X1 Carbon Gen 11",
        "brand": "Lenovo",
        "category": "laptop",
        "price": 38990000,
        "specs": {
            "cpu": "Intel Core i7-1365U (10-core)",
            "ram": "16GB LPDDR5",
            "storage": "512GB SSD",
            "display": "14\" IPS 2.8K, 90Hz",
            "gpu": "Intel Iris Xe Graphics",
            "battery": "15 giờ",
            "weight": "1.12kg",
            "os": "Windows 11 Pro",
            "ports": "2x Thunderbolt 4, 2x USB-A, HDMI, SD Card",
        },
        "highlight": "Siêu nhẹ 1.12kg, lý tưởng cho doanh nhân và di chuyển nhiều",
        "use_cases": ["văn phòng", "di chuyển", "lập trình", "hội họp", "thuyết trình"],
        "pros": ["Siêu nhẹ 1.12kg", "Bàn phím tốt nhất", "Pin 15 giờ", "Bảo mật doanh nghiệp"],
        "cons": ["Không có GPU rời", "Không phù hợp đồ họa nặng", "Màn hình không OLED"],
        "stock": 10,
        "rating": 4.8,
        "tags": ["nhẹ nhất", "văn phòng", "doanh nhân", "di chuyển", "bền", "lập trình"],
    },
    {
        "id": "LP004",
        "name": "ASUS ROG Strix G16 2024",
        "brand": "ASUS",
        "category": "laptop",
        "price": 32990000,
        "specs": {
            "cpu": "AMD Ryzen 9 8945HX (16-core)",
            "ram": "32GB DDR5",
            "storage": "1TB NVMe SSD",
            "display": "16\" QHD+ 240Hz, 100% sRGB",
            "gpu": "NVIDIA RTX 4070 8GB",
            "battery": "8 giờ",
            "weight": "2.5kg",
            "os": "Windows 11 Home",
            "ports": "USB-C (TB4), 3x USB-A, HDMI 2.1, SD Card",
        },
        "highlight": "Laptop gaming mạnh nhất tầm 33 triệu",
        "use_cases": ["gaming", "đồ họa", "render 3D", "streaming", "AI/ML"],
        "pros": ["RTX 4070", "RAM 32GB", "Màn hình 240Hz", "Ryzen 9 mạnh"],
        "cons": ["Nặng 2.5kg", "Pin ngắn", "Không phù hợp di chuyển nhiều"],
        "stock": 6,
        "rating": 4.6,
        "tags": ["gaming", "RTX", "240Hz", "mạnh", "đồ họa", "render"],
    },
    {
        "id": "LP005",
        "name": "HP Spectre x360 14",
        "brand": "HP",
        "category": "laptop",
        "price": 28990000,
        "specs": {
            "cpu": "Intel Core Ultra 7 155H",
            "ram": "16GB LPDDR5",
            "storage": "512GB SSD",
            "display": "14\" OLED 2.8K, 120Hz, cảm ứng, xoay 360°",
            "gpu": "Intel Arc Graphics",
            "battery": "17 giờ",
            "weight": "1.57kg",
            "os": "Windows 11 Home",
            "ports": "2x Thunderbolt 4, USB-A, 3.5mm",
        },
        "highlight": "2-in-1 cao cấp với màn hình OLED cảm ứng xoay 360°",
        "use_cases": ["văn phòng", "vẽ tay", "đọc tài liệu", "thuyết trình", "giải trí"],
        "pros": ["OLED cảm ứng đẹp", "Xoay 360°", "Pin 17 giờ", "Thiết kế sang"],
        "cons": ["Không GPU rời mạnh", "Giá cao so với cấu hình"],
        "stock": 9,
        "rating": 4.7,
        "tags": ["2-in-1", "cảm ứng", "OLED", "xoay", "văn phòng", "mỏng nhẹ"],
    },
    {
        "id": "LP006",
        "name": "Acer Aspire 5 A515 i5-1235U",
        "brand": "Acer",
        "category": "laptop",
        "price": 14990000,
        "specs": {
            "cpu": "Intel Core i5-1235U (10-core)",
            "ram": "8GB DDR4 (nâng cấp được lên 32GB)",
            "storage": "512GB SSD",
            "display": "15.6\" Full HD IPS 60Hz",
            "gpu": "Intel Iris Xe Graphics",
            "battery": "9 giờ",
            "weight": "1.8kg",
            "os": "Windows 11 Home",
            "ports": "USB-C, 2x USB-A, HDMI, SD Card, 3.5mm",
        },
        "highlight": "Laptop phổ thông giá tốt, đáp ứng học tập & văn phòng",
        "use_cases": ["học tập", "văn phòng", "lập trình cơ bản", "giải trí nhẹ"],
        "pros": ["Giá phải chăng", "Cổng kết nối đầy đủ", "RAM nâng cấp được", "Bền"],
        "cons": ["Màn hình 60Hz", "Không GPU rời", "Thiết kế không nổi bật"],
        "stock": 20,
        "rating": 4.4,
        "tags": ["giá rẻ", "học sinh", "sinh viên", "văn phòng", "phổ thông", "tiết kiệm"],
    },

    # ──────────────────── ĐIỆN THOẠI ────────────────────
    {
        "id": "PH001",
        "name": "iPhone 15 Pro Max 256GB",
        "brand": "Apple",
        "category": "phone",
        "price": 34990000,
        "specs": {
            "cpu": "Apple A17 Pro (3nm)",
            "ram": "8GB",
            "storage": "256GB",
            "display": "6.7\" Super Retina XDR OLED, 120Hz ProMotion, Always-On",
            "camera": "48MP + 12MP + 12MP (5x optical zoom)",
            "battery": "4422mAh, 29W wired, 15W MagSafe",
            "os": "iOS 17",
            "connectivity": "5G, WiFi 6E, Bluetooth 5.3, USB-C 3.0",
            "build": "Titanium frame + Ceramic Shield",
        },
        "highlight": "iPhone tốt nhất hiện tại với khung titanium và camera 5x zoom",
        "use_cases": ["chụp ảnh", "quay phim", "mạng xã hội", "cao cấp", "business"],
        "pros": ["Camera 5x zoom tuyệt vời", "Hiệu năng A17 Pro", "Build titanium", "Ecosystem Apple"],
        "cons": ["Giá cao", "Sạc chậm hơn Android", "Không có sạc trong hộp"],
        "stock": 25,
        "rating": 4.9,
        "tags": ["camera", "iOS", "cao cấp", "titanium", "5G", "chụp ảnh đẹp"],
    },
    {
        "id": "PH002",
        "name": "Samsung Galaxy S24 Ultra 256GB",
        "brand": "Samsung",
        "category": "phone",
        "price": 31990000,
        "specs": {
            "cpu": "Snapdragon 8 Gen 3",
            "ram": "12GB",
            "storage": "256GB",
            "display": "6.8\" Dynamic AMOLED 2X, 120Hz, 2600 nits",
            "camera": "200MP + 10MP + 50MP + 12MP (10x optical zoom)",
            "battery": "5000mAh, 45W wired, 15W wireless",
            "os": "Android 14 + One UI 6.1",
            "connectivity": "5G, WiFi 7, Bluetooth 5.3, USB-C 3.2",
            "special": "S Pen tích hợp, AI Galaxy",
        },
        "highlight": "Camera 200MP + S Pen + AI mạnh nhất trong các flagship Android",
        "use_cases": ["chụp ảnh chuyên nghiệp", "ghi chú S Pen", "business", "đa nhiệm"],
        "pros": ["Camera 200MP + 10x zoom", "S Pen tiện dụng", "Màn hình sáng nhất", "AI tích hợp"],
        "cons": ["Giá cao", "Thân dày hơn", "Tiêu hao pin nhanh hơn"],
        "stock": 18,
        "rating": 4.8,
        "tags": ["camera", "S Pen", "AI", "200MP", "Android", "cao cấp", "zoom xa"],
    },
    {
        "id": "PH003",
        "name": "Xiaomi 14 Ultra",
        "brand": "Xiaomi",
        "category": "phone",
        "price": 23990000,
        "specs": {
            "cpu": "Snapdragon 8 Gen 3",
            "ram": "16GB LPDDR5X",
            "storage": "512GB UFS 4.0",
            "display": "6.73\" LTPO AMOLED, 120Hz, 3000 nits",
            "camera": "50MP (Leica) + 50MP + 50MP + 50MP (5x zoom)",
            "battery": "5000mAh, 90W wired, 80W wireless, 10W reverse",
            "os": "Android 14 + HyperOS",
            "connectivity": "5G, WiFi 7, Bluetooth 5.4",
        },
        "highlight": "Camera Leica đỉnh cao, giá tốt hơn đối thủ tầm trên",
        "use_cases": ["chụp ảnh", "quay phim", "gaming nhẹ", "content creator"],
        "pros": ["Camera Leica 50MP x4", "Sạc 90W siêu nhanh", "RAM 16GB", "Giá tốt hơn iPhone/Samsung"],
        "cons": ["Không có Google Play sẵn (cần cài thêm ở VN)", "MIUI đôi khi lag"],
        "stock": 14,
        "rating": 4.7,
        "tags": ["Leica", "camera", "sạc nhanh", "flagship", "Xiaomi", "giá tốt"],
    },
    {
        "id": "PH004",
        "name": "Samsung Galaxy A55 5G 256GB",
        "brand": "Samsung",
        "category": "phone",
        "price": 10990000,
        "specs": {
            "cpu": "Exynos 1480 (4nm)",
            "ram": "8GB (ảo thêm 8GB)",
            "storage": "256GB",
            "display": "6.6\" Super AMOLED FHD+, 120Hz",
            "camera": "50MP + 12MP + 5MP",
            "battery": "5000mAh, 25W",
            "os": "Android 14 + One UI 6.1",
            "connectivity": "5G, WiFi 6, Bluetooth 5.3",
        },
        "highlight": "Samsung tầm trung tốt nhất: màn đẹp, camera ổn, giá phải chăng",
        "use_cases": ["sử dụng hàng ngày", "mạng xã hội", "chụp ảnh cơ bản", "gaming nhẹ"],
        "pros": ["Màn AMOLED đẹp 120Hz", "Thiết kế cao cấp", "5 năm cập nhật OS", "Pin lâu"],
        "cons": ["Chip Exynos không mạnh bằng Snapdragon", "Sạc 25W chậm"],
        "stock": 30,
        "rating": 4.5,
        "tags": ["tầm trung", "Samsung", "AMOLED", "5G", "giá tốt", "pin lâu"],
    },
    {
        "id": "PH005",
        "name": "Xiaomi Redmi Note 13 Pro 5G 256GB",
        "brand": "Xiaomi",
        "category": "phone",
        "price": 7490000,
        "specs": {
            "cpu": "Snapdragon 7s Gen 2",
            "ram": "8GB",
            "storage": "256GB",
            "display": "6.67\" AMOLED FHD+, 120Hz, 1800 nits",
            "camera": "200MP + 8MP + 2MP",
            "battery": "5100mAh, 67W",
            "os": "Android 13 + MIUI 14",
            "connectivity": "5G, WiFi 6, Bluetooth 5.2",
        },
        "highlight": "Camera 200MP giá rẻ nhất thị trường, sạc 67W siêu nhanh",
        "use_cases": ["học sinh", "sinh viên", "sử dụng hàng ngày", "chụp ảnh"],
        "pros": ["Camera 200MP", "Sạc 67W nhanh", "Màn AMOLED 120Hz", "Giá cực tốt"],
        "cons": ["MIUI nhiều quảng cáo", "Không flagship specs", "Camera đêm trung bình"],
        "stock": 40,
        "rating": 4.4,
        "tags": ["giá rẻ", "200MP", "sạc nhanh", "học sinh", "tầm thấp", "tiết kiệm"],
    },

    # ──────────────────── MÁY TÍNH BẢNG ────────────────────
    {
        "id": "TB001",
        "name": "iPad Pro M4 13\" WiFi 256GB",
        "brand": "Apple",
        "category": "tablet",
        "price": 32990000,
        "specs": {
            "cpu": "Apple M4 (10-core)",
            "ram": "8GB",
            "storage": "256GB",
            "display": "13\" Ultra Retina XDR OLED tandem, 120Hz ProMotion",
            "camera": "12MP (sau) + 12MP (trước TrueDepth)",
            "battery": "10 giờ",
            "weight": "582g",
            "os": "iPadOS 17",
            "connectivity": "WiFi 6E, Bluetooth 5.3, USB-C Thunderbolt 4",
            "accessories": "Hỗ trợ Apple Pencil Pro, Magic Keyboard",
        },
        "highlight": "Máy tính bảng mạnh nhất thế giới với màn OLED tandem",
        "use_cases": ["vẽ kỹ thuật số", "đọc tài liệu", "thiết kế", "giải trí cao cấp", "làm việc"],
        "pros": ["Màn OLED Tandem đẹp nhất", "M4 cực mạnh", "Mỏng nhất thế giới", "Apple Pencil Pro"],
        "cons": ["Giá cao", "iPadOS hạn chế hơn macOS", "Phụ kiện bán riêng"],
        "stock": 10,
        "rating": 4.9,
        "tags": ["cao cấp", "OLED", "vẽ", "thiết kế", "mỏng nhất", "M4", "Apple Pencil"],
    },
    {
        "id": "TB002",
        "name": "Samsung Galaxy Tab S9 Ultra WiFi 256GB",
        "brand": "Samsung",
        "category": "tablet",
        "price": 26990000,
        "specs": {
            "cpu": "Snapdragon 8 Gen 2",
            "ram": "12GB",
            "storage": "256GB",
            "display": "14.6\" Dynamic AMOLED 2X, 120Hz, HDR10+",
            "camera": "13MP + 8MP (sau) + 12MP + 12MP (trước)",
            "battery": "11200mAh, 45W",
            "weight": "732g",
            "os": "Android 13 + One UI 5.1",
            "connectivity": "WiFi 6E, Bluetooth 5.3, USB-C 3.2",
            "accessories": "S Pen trong hộp",
        },
        "highlight": "Màn hình AMOLED 14.6\" lớn nhất + S Pen trong hộp",
        "use_cases": ["vẽ S Pen", "xem phim", "đọc tài liệu", "làm việc", "giải trí"],
        "pros": ["Màn 14.6\" cực lớn", "S Pen trong hộp", "Pin 11200mAh", "DeX mode"],
        "cons": ["Nặng 732g", "Giá cao", "Android tablet app hạn chế hơn iPad"],
        "stock": 7,
        "rating": 4.7,
        "tags": ["14.6 inch", "S Pen", "AMOLED", "lớn nhất", "Android", "xem phim"],
    },
    {
        "id": "TB003",
        "name": "iPad Air M2 11\" WiFi 128GB",
        "brand": "Apple",
        "category": "tablet",
        "price": 18990000,
        "specs": {
            "cpu": "Apple M2 (8-core)",
            "ram": "8GB",
            "storage": "128GB",
            "display": "11\" Liquid Retina IPS, 60Hz, True Tone",
            "camera": "12MP (sau) + 12MP landscape (trước)",
            "battery": "10 giờ",
            "weight": "461g",
            "os": "iPadOS 17",
            "connectivity": "WiFi 6, Bluetooth 5.3, USB-C",
            "accessories": "Hỗ trợ Apple Pencil 2, Magic Keyboard",
        },
        "highlight": "iPad cân bằng nhất: M2 mạnh, giá vừa phải, nhẹ 461g",
        "use_cases": ["học tập", "ghi chú", "vẽ", "giải trí", "làm việc nhẹ"],
        "pros": ["Nhẹ 461g", "M2 mạnh mẽ", "Giá tốt hơn iPad Pro", "Camera trước landscape"],
        "cons": ["Màn 60Hz", "Lưu trữ 128GB không nhiều", "Không OLED"],
        "stock": 15,
        "rating": 4.8,
        "tags": ["nhẹ", "M2", "học tập", "vẽ", "Apple Pencil", "tầm trung", "cân bằng"],
    },
    {
        "id": "TB004",
        "name": "Xiaomi Pad 6 Pro 8GB/256GB",
        "brand": "Xiaomi",
        "category": "tablet",
        "price": 9990000,
        "specs": {
            "cpu": "Snapdragon 8+ Gen 1",
            "ram": "8GB LPDDR5",
            "storage": "256GB UFS 3.1",
            "display": "11\" IPS LCD 2.8K, 144Hz",
            "camera": "50MP (sau) + 20MP (trước)",
            "battery": "8600mAh, 67W",
            "weight": "490g",
            "os": "Android 13 + MIUI 14 Pad",
            "connectivity": "WiFi 6, Bluetooth 5.3, USB-C",
        },
        "highlight": "Máy tính bảng Android giá tốt nhất: Snapdragon 8+, 144Hz",
        "use_cases": ["học tập", "xem phim", "gaming", "giải trí", "đọc sách"],
        "pros": ["Giá rẻ nhất phân khúc", "144Hz mượt", "Snapdragon 8+", "Sạc 67W"],
        "cons": ["MIUI nhiều quảng cáo", "Camera trung bình", "Không hỗ trợ stylus chính hãng"],
        "stock": 22,
        "rating": 4.5,
        "tags": ["giá rẻ", "144Hz", "Android", "gaming", "học tập", "tiết kiệm", "Xiaomi"],
    },
]


# ── Live product list (updated from DB at runtime) ─────────────────────────────
_live_products: List[dict] = list(PRODUCTS_DB)


def reload_products() -> None:
    """Replace the live list with the current DB state. Called after admin CRUD."""
    global _live_products
    try:
        from db.database import load_all_products
        db_products = load_all_products()
        _live_products = db_products if db_products else list(PRODUCTS_DB)
    except Exception:
        _live_products = list(PRODUCTS_DB)


def get_live_products() -> List[dict]:
    return _live_products


def search_products(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    brand: Optional[str] = None,
    use_case: Optional[str] = None,
    keywords: Optional[list] = None,
) -> List[dict]:
    results = list(_live_products)

    if category:
        cat = category.lower()
        results = [p for p in results if p["category"].lower() == cat]

    if max_price:
        results = [p for p in results if p["price"] <= max_price]

    if min_price:
        results = [p for p in results if p["price"] >= min_price]

    if brand:
        b = brand.lower()
        results = [p for p in results if b in p["brand"].lower()]

    if use_case:
        uc = use_case.lower()
        results = [
            p for p in results
            if any(uc in u.lower() for u in p.get("use_cases", []))
            or any(uc in t.lower() for t in p.get("tags", []))
            or uc in p.get("highlight", "").lower()
        ]

    if keywords:
        kw_lower = [k.lower() for k in keywords if k]
        def matches_keywords(product):
            text = (
                product["name"].lower()
                + " " + product["brand"].lower()
                + " " + product.get("highlight", "").lower()
                + " " + " ".join(product.get("tags", []))
                + " " + " ".join(product.get("use_cases", []))
            )
            return any(kw in text for kw in kw_lower)
        filtered = [p for p in results if matches_keywords(p)]
        if filtered:
            results = filtered

    # Sort by rating desc
    results.sort(key=lambda p: p["rating"], reverse=True)
    return results


def get_product_by_id(product_id: str) -> Optional[dict]:
    for p in _live_products:
        if p["id"] == product_id:
            return p
    return None


def format_price(price: int) -> str:
    return f"{price:,}đ".replace(",", ".")


def format_products_for_llm(products: List[dict]) -> str:
    lines = []
    for p in products:
        specs = p["specs"]
        lines.append(
            f"[{p['id']}] {p['name']} — {format_price(p['price'])}\n"
            f"  Điểm nổi bật: {p['highlight']}\n"
            f"  Specs chính: CPU {specs.get('cpu','N/A')} | RAM {specs.get('ram','N/A')} | "
            f"Storage {specs.get('storage','N/A')} | Display {specs.get('display','N/A')}\n"
            f"  Pin: {specs.get('battery','N/A')} | Trọng lượng: {specs.get('weight','N/A')}\n"
            f"  Ưu điểm: {', '.join(p.get('pros', []))}\n"
            f"  Tồn kho: {p['stock']} cái | Rating: {p['rating']}/5\n"
        )
    return "\n".join(lines)
