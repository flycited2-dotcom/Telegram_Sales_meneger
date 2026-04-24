"""Catalog search and deterministic sales-response helpers."""

from __future__ import annotations

import re
from typing import Optional

from database import load_products

_STOP = {
    "нужен", "нужна", "нужно", "нужны", "хочу", "хотим", "хотите", "дайте", "покажи",
    "покажите", "расскажи", "расскажите", "купить", "куплю", "заказать", "подберите",
    "подбери", "помогите", "помоги", "ищу", "найдите", "интересует", "интересуют",
    "скажи", "скажите", "могу", "можно", "можете", "привезете", "доставка", "есть",
    "ли", "что", "как", "где", "какой", "какая", "какие", "каких", "чего", "кому",
    "зачем", "почему", "когда", "куда", "откуда", "это", "этот", "эта", "эти",
    "того", "самый", "самая", "свой", "своя", "свои", "меня", "мне", "вас", "вам",
    "его", "ее", "их", "ими", "про", "для", "из", "от", "до", "за", "при", "под",
    "над", "без", "со", "и", "в", "на", "с", "по", "но", "так", "не", "у", "а",
    "к", "об", "обо", "нет", "да", "ну", "ок", "окей", "ладно", "хорошо", "понятно",
    "именно", "точно", "конечно", "спасибо", "пожалуйста", "надо", "все", "ничего",
    "ниче", "привет", "здравствуйте", "добрый", "день", "утро", "вечер", "пока",
    "ага", "угу", "ясно", "давай", "давайте", "понял", "поняла", "нормально",
    "блин", "эй", "ой", "ай", "ух", "хм", "эм", "стоит", "цена", "цены", "руб", "рублей",
    "рубль", "штук", "шт", "дешево", "дешевле", "дорого", "дороже", "бюджет",
    "бюджета", "бесплатно", "поставь", "ставь", "оформи", "запиши", "выбери",
    "заказ", "заказа", "заявку", "заявка", "одно", "одна", "одну", "один", "оба",
    "обе", "несколько", "пару", "любой", "которая", "который", "которое", "которые",
    "такой", "такая", "такие", "последний", "очень", "более", "менее", "лучше",
    "хуже", "больше", "меньше", "также", "тоже", "еще", "просто", "только", "уже",
    "самое",
}

_SELECTION_WORDS = {
    "беру", "возьму", "оформляй", "оформить", "первый", "второй", "третий",
    "эту", "этот", "эти", "его", "ее", "их",
}

_PRICE_QUERY_WORDS = {
    "цена", "цены", "по цене", "стоимость", "сколько стоит", "подешевле", "недорогой",
    "недорогие", "дорогой", "дорогие", "бюджет", "бюджетный",
}

_GREETING_WORDS = {"привет", "здравствуйте", "добрый", "день", "утро", "вечер"}
_META_WORDS = {
    "супер", "класс", "ок", "окей", "понял", "понятно", "ясно", "ага", "угу",
    "опять", "бред", "поплыл", "стоп", "хватит", "зачем", "прислал", "шлешь",
}
_COMPLAINT_PHRASES = {"не просил", "не спрашивал", "что ты мне шлешь", "ты поплыл"}
_REQUIRED_TOKENS = {"инвертор", "сух", "тен"}
_APPLIANCE_TOKENS = {
    "кондиционер", "водонагреватель", "микроволновая", "стиральная",
    "холодильник", "телевизор", "посудомоечная", "морозильная",
}
_ACCESSORY_WORDS = {
    "кронштейн", "ножи", "фильтр", "пульт", "шланг", "кабель", "насадка",
    "форма", "труба", "подставка", "держатель", "крепление",
}

_ORDINAL_MAP = {
    "первый": 0,
    "1": 0,
    "1й": 0,
    "1-й": 0,
    "второй": 1,
    "2": 1,
    "2й": 1,
    "2-й": 1,
    "третий": 2,
    "3": 2,
    "3й": 2,
    "3-й": 2,
}

_SYNONYMS = {
    "кондер": "кондиционер",
    "кондеры": "кондиционер",
    "кондёр": "кондиционер",
    "кондёры": "кондиционер",
    "сплит": "кондиционер",
    "сплиты": "кондиционер",
    "стиралка": "стиральная",
    "стиралки": "стиральная",
    "холодос": "холодильник",
    "бойлер": "водонагреватель",
    "бойлеры": "водонагреватель",
    "сухим": "сух",
    "сухой": "сух",
    "сухого": "сух",
    "тэн": "тен",
    "тэном": "тен",
    "тена": "тен",
    "теном": "тен",
    "инвертор": "инвертор",
    "инверторный": "инвертор",
    "инверторная": "инвертор",
    "телик": "телевизор",
    "телики": "телевизор",
    "ноут": "ноутбук",
    "ноуты": "ноутбук",
    "комп": "компьютер",
    "компы": "компьютер",
    "духовка": "духовой",
    "духовки": "духовой",
    "варочка": "варочная",
    "индукция": "варочная",
    "микруха": "микроволновая",
    "микроволновка": "микроволновая",
    "микроволновки": "микроволновая",
    "свч": "микроволновая",
    "посудомойка": "посудомоечная",
    "морозилка": "морозильная",
    "дуйчик": "вентилятор",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def _parse_int(raw: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def extract_price_range(text: str) -> tuple[Optional[int], Optional[int]]:
    text_l = _normalize_text(text)

    match = re.search(r"от\s*([\d\s]+)\s*до\s*([\d\s]+)", text_l)
    if match:
        return _parse_int(match.group(1)), _parse_int(match.group(2))

    match = re.search(r"([\d\s]{3,})\s*[-–]\s*([\d\s]{3,})", text_l)
    if match:
        return _parse_int(match.group(1)), _parse_int(match.group(2))

    match = re.search(r"до\s*([\d\s]+)", text_l)
    if match:
        return None, _parse_int(match.group(1))

    match = re.search(r"от\s*([\d\s]+)", text_l)
    if match:
        return _parse_int(match.group(1)), None

    return None, None


def _budget_numbers(text: str) -> set[str]:
    lower, upper = extract_price_range(text)
    values: set[str] = set()
    if lower is not None:
        values.add(str(lower))
    if upper is not None:
        values.add(str(upper))
    return values


def _tokenize(text: str) -> list[str]:
    raw = re.findall(r"[a-zа-яё0-9-]+", text.lower())
    budget_numbers = _budget_numbers(text)
    tokens: list[str] = []
    for token in raw:
        token = token.strip("-")
        token = _SYNONYMS.get(token, token)
        if token in budget_numbers:
            continue
        digits = re.sub(r"[^\d]", "", token)
        if digits and token not in budget_numbers and token not in _STOP:
            if token.isdigit():
                tokens.append(token)
                continue
            if re.fullmatch(r"\d+[а-яa-z-]*", token):
                tokens.append(digits)
                continue
        if len(token) <= 1 or token in _STOP:
            continue
        token = re.sub(r"[^a-zа-яё0-9]+", "", token)
        if token and token not in _STOP:
            tokens.append(token)
    return tokens


def is_selection_message(text: str) -> bool:
    text_l = _normalize_text(text)
    return any(word in text_l for word in _SELECTION_WORDS)


def is_price_query(text: str) -> bool:
    text_l = _normalize_text(text)
    return any(word in text_l for word in _PRICE_QUERY_WORDS) or any(extract_price_range(text))


def is_greeting(text: str) -> bool:
    text_l = _normalize_text(text)
    return any(word in text_l.split() for word in _GREETING_WORDS)


def is_meta_message(text: str) -> bool:
    text_l = _normalize_text(text)
    if any(phrase in text_l for phrase in _COMPLAINT_PHRASES):
        return True
    if len(text_l) <= 2:
        return True
    tokens = set(_tokenize(text))
    return bool(tokens) and tokens.issubset(_META_WORDS)


def has_catalog_intent(text: str, has_context: bool = False) -> bool:
    if is_greeting(text) or is_meta_message(text):
        return False
    if is_selection_message(text):
        return has_context
    tokens = _tokenize(text)
    if tokens:
        return True
    return bool(has_context and is_price_query(text))


def _status_label(product: dict) -> str:
    stock = int(product.get("stock", 0) or 0)
    if stock > 0:
        return f"в наличии {stock} шт"
    return "в наличии"


def _discount_for_quantity(product: dict, quantity: int) -> int:
    best = 0
    for raw_threshold, raw_discount in (product.get("discounts") or {}).items():
        match = re.match(r"(\d+)\+?", str(raw_threshold).strip())
        if not match:
            continue
        threshold = int(match.group(1))
        discount = int(raw_discount)
        if quantity >= threshold:
            best = max(best, discount)
    return best


def price_for_quantity(product: dict, quantity: int) -> tuple[float, int]:
    base_price = float(product["price"])
    discount_pct = _discount_for_quantity(product, quantity)
    if discount_pct <= 0:
        return round(base_price, 2), 0
    discounted = round(base_price * (100 - discount_pct) / 100, 2)
    return discounted, discount_pct


def get_products_by_ids(product_ids: list[str]) -> list[dict]:
    ids = {str(product_id).strip().lower() for product_id in product_ids if str(product_id).strip()}
    if not ids:
        return []
    products = []
    for product in load_products():
        if str(product.get("id", "")).strip().lower() in ids:
            products.append(product)
    return products


def search_products(
    query: str,
    limit: Optional[int] = 12,
    *,
    preferred_product_ids: Optional[list[str]] = None,
    ignore_price: bool = False,
) -> list[dict]:
    products = load_products()
    tokens = _tokenize(query)
    has_budget = is_price_query(query)
    price_min, price_max = extract_price_range(query)
    text_tokens = [token for token in tokens if not token.isdigit()]
    number_tokens = [token for token in tokens if token.isdigit()]
    preferred_ids = {str(product_id).strip().lower() for product_id in (preferred_product_ids or [])}
    use_context_only = bool(preferred_ids and has_budget and not text_tokens and not number_tokens)
    if use_context_only:
        preferred = get_products_by_ids(preferred_product_ids or [])
        if preferred:
            products = preferred

    if not products or (not tokens and not has_budget):
        return []

    scored: list[tuple[int, dict]] = []

    for product in products:
        price = float(product["price"])
        if not ignore_price and price_min is not None and price < price_min:
            continue
        if not ignore_price and price_max is not None and price > price_max:
            continue

        name_l = _normalize_text(product["name"])
        cat_l = _normalize_text(product.get("category", ""))
        desc_l = _normalize_text(product.get("description", ""))
        sku_l = _normalize_text(product.get("supplier_sku", ""))
        full = f"{name_l} {cat_l} {desc_l} {sku_l}"
        full_search = f"{full} {' '.join(_tokenize(full))}"
        score = 0

        if any(token in _REQUIRED_TOKENS and token not in full_search for token in text_tokens):
            continue
        if any(token in _APPLIANCE_TOKENS for token in text_tokens):
            if any(word in name_l for word in _ACCESSORY_WORDS) and not any(word in text_tokens for word in _ACCESSORY_WORDS):
                continue

        if text_tokens:
            text_hits = 0
            for token in text_tokens:
                if token in name_l:
                    score += 5
                    text_hits += 1
                elif token in cat_l:
                    score += 4
                    text_hits += 1
                elif token in desc_l or token in sku_l or token in full_search:
                    score += 2
                    text_hits += 1
            if text_hits == 0:
                continue

        if number_tokens:
            number_hits = 0
            for token in number_tokens:
                if re.search(rf"(?<!\d){re.escape(token)}(?!\d)", full_search):
                    score += 6
                    number_hits += 1
                elif token in full_search:
                    score += 1
            if number_hits == 0:
                continue

        if has_budget:
            score += 2
        if str(product.get("id", "")).strip().lower() in preferred_ids:
            score += 3

        if score >= 4:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], float(item[1]["price"])))
    results = [product for _, product in scored]
    return results[:limit] if limit else results


def render_catalog_context(
    query: str,
    limit: int = 12,
    *,
    preferred_product_ids: Optional[list[str]] = None,
) -> tuple[str, list[dict]]:
    products = load_products()
    if not products:
        return "[КАТАЛОГ]\nСтатус: пусто", []

    has_context = bool(preferred_product_ids)
    if not has_catalog_intent(query, has_context=has_context):
        return "[КАТАЛОГ]\nСтатус: не задействован", []

    matches = search_products(query, limit=limit, preferred_product_ids=preferred_product_ids)
    if not matches:
        return "[КАТАЛОГ]\nСтатус: товар не найден", []

    lines = [f"[КАТАЛОГ]\nСтатус: найдено {len(matches)} позиций"]
    for product in matches:
        lines.append(
            "ID: {id} | {name} | Цена: {price:.0f} ₽ | {status}".format(
                id=product["id"],
                name=product["name"],
                price=float(product["price"]),
                status=_status_label(product),
            )
        )
    return "\n".join(lines), matches


def build_sales_listing(query: str, matches: list[dict]) -> Optional[str]:
    if not matches or is_selection_message(query) or is_greeting(query) or is_meta_message(query):
        return None

    price_min, price_max = extract_price_range(query)
    if is_price_query(query) and price_min is None and price_max is None:
        return "По какому бюджету показать варианты? Напишите, например: до 30000 или от 25000 до 40000."

    if is_price_query(query) and not _tokenize(query):
        return "По какому товару показать варианты в этом бюджете?"

    lines = [f"Подобрал варианты ({len(matches)}), все из наличия:"]
    for index, product in enumerate(matches, start=1):
        lines.append(f"{index}. {product['name']} — {float(product['price']):,.0f} ₽, {_status_label(product)}")
    if len(matches) >= 10:
        lines.append("Если нужно, сузим выбор по бюджету, бренду или объему.")
    else:
        lines.append("Если подходит, напишите модель или номер из списка.")
    return "\n".join(lines)


def build_no_match_reply(query: str, had_context: bool = False, alternatives: Optional[list[dict]] = None) -> Optional[str]:
    if not has_catalog_intent(query, has_context=had_context):
        return None
    if alternatives:
        lines = ["В этом бюджете точного варианта не вижу. Ближайшие позиции в наличии:"]
        for index, product in enumerate(alternatives, start=1):
            lines.append(f"{index}. {product['name']} — {float(product['price']):,.0f} ₽, {_status_label(product)}")
        lines.append("Если бюджет можно поднять, оформим один из этих вариантов. Если нет, посмотрю другую категорию.")
        return "\n".join(lines)
    if had_context and is_price_query(query):
        return "В этом бюджете по последнему подбору подходящих позиций не вижу. Могу расширить бюджет или посмотреть соседние модели."
    return "По этому запросу в каталоге точного совпадения не вижу. Напишите категорию, бренд, объем или бюджет, и я подберу ближе."


def build_selection_reply(query: str, context_products: list[dict]) -> Optional[str]:
    if not is_selection_message(query) or not context_products:
        return None

    text_l = _normalize_text(query)
    for marker, index in _ORDINAL_MAP.items():
        if re.search(rf"(^|\s){re.escape(marker)}($|\s)", text_l) and index < len(context_products):
            product = context_products[index]
            return (
                f"Принял. Можно оформить {product['name']}.\n"
                "Напишите имя, телефон и количество."
            )

    return "Напишите модель из последнего списка и сразу имя, телефон и количество."


def build_smalltalk_reply(query: str, has_context: bool = False) -> Optional[str]:
    if is_greeting(query):
        return "Здравствуйте. Что именно подобрать: кондиционер, бойлер, микроволновку или другой товар?"
    if is_meta_message(query):
        if has_context:
            return "Понял. Давайте по делу: напишите товар, бюджет или ключевой параметр, и я подберу нормально."
        return "Понял. Напишите, какой товар нужен, и я сразу покажу подходящие варианты."
    return None


def get_product_by_id(product_id: str) -> Optional[dict]:
    normalized = str(product_id).strip().lower()
    if not normalized:
        return None
    for product in load_products():
        if str(product.get("id", "")).strip().lower() == normalized:
            return product
    return None


def get_product_by_name(product_name: str) -> Optional[dict]:
    normalized = _normalize_text(product_name)
    if not normalized:
        return None
    for product in load_products():
        if _normalize_text(product.get("name", "")) == normalized:
            return product
    return None


def resolve_catalog_product(product_id: str = "", product_name: str = "") -> Optional[dict]:
    return get_product_by_id(product_id) or get_product_by_name(product_name)
