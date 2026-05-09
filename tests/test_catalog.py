import unittest
from unittest.mock import patch

from catalog import (
    build_selection_reply,
    build_smalltalk_reply,
    price_for_quantity,
    render_catalog_context,
    resolve_catalog_product,
    search_alternatives,
    search_products,
    select_product_from_context,
)


CATALOG_FIXTURE = [
    {
        "id": "AC-12",
        "name": "Dahatsu Кондиционер 12 ONYX",
        "description": "Инверторная сплит-система",
        "price": 25000.0,
        "stock": 3,
        "unit": "шт",
        "category": "Кондиционеры",
        "supplier_sku": "DH-12-ONYX",
        "discounts": {"5+": 7},
    },
    {
        "id": "AC-09",
        "name": "Dahatsu Кондиционер 09 ONYX",
        "description": "Инверторная сплит-система",
        "price": 22000.0,
        "stock": 2,
        "unit": "шт",
        "category": "Кондиционеры",
        "supplier_sku": "DH-09-ONYX",
        "discounts": {},
    },
    {
        "id": "BOILER-80",
        "name": "Thermex Водонагреватель 80 сухой тэн",
        "description": "Накопительный",
        "price": 18000.0,
        "stock": 0,
        "unit": "шт",
        "category": "Водонагреватели",
        "supplier_sku": "TMX-80",
        "discounts": {},
    },
    {
        "id": "BOILER-50",
        "name": "Oasis Водонагреватель 50 сухой тэн",
        "description": "Накопительный",
        "price": 7800.0,
        "stock": 4,
        "unit": "шт",
        "category": "Водонагреватели",
        "supplier_sku": "OAS-50",
        "discounts": {},
    },
    {
        "id": "MW-1",
        "name": "Midea Микроволновая печь 20л",
        "description": "СВЧ",
        "price": 3900.0,
        "stock": 3,
        "unit": "шт",
        "category": "Микроволновые печи",
        "supplier_sku": "MW-20",
        "discounts": {},
    },
    {
        "id": "MW-BRACKET",
        "name": "I-Tech Кронштейн для СВЧ",
        "description": "Аксессуар",
        "price": 900.0,
        "stock": 10,
        "unit": "шт",
        "category": "Аксессуары",
        "supplier_sku": "MW-BR",
        "discounts": {},
    },
    {
        "id": "AC-35",
        "name": "Chigo Кондиционер 35",
        "description": "Сплит-система на 35 м2",
        "price": 24171.0,
        "stock": 2,
        "unit": "шт",
        "category": "Кондиционеры",
        "supplier_sku": "AC-35",
        "discounts": {},
    },
    {
        "id": "MW-35",
        "name": "LG СВЧ печь MB63W35GIB",
        "description": "23л",
        "price": 13770.0,
        "stock": 1,
        "unit": "шт",
        "category": "Микроволновые печи",
        "supplier_sku": "MW-35",
        "discounts": {},
    },
    {
        "id": "GREEN-1",
        "name": "ATLANTA Весы кухонные green",
        "description": "",
        "price": 730.0,
        "stock": 1,
        "unit": "шт",
        "category": "Весы",
        "supplier_sku": "GREEN",
        "discounts": {},
    },
    {
        "id": "GREE-1",
        "name": "Gree Кондиционер 12 Pular",
        "description": "",
        "price": 45423.0,
        "stock": 1,
        "unit": "шт",
        "category": "Кондиционеры",
        "supplier_sku": "GREE-12",
        "discounts": {},
    },
    {
        "id": "HOOD-1",
        "name": "Evelux Вытяжка Ulla 60 W",
        "description": "",
        "price": 3717.0,
        "stock": 4,
        "unit": "шт",
        "category": "Вытяжки",
        "supplier_sku": "HOOD-1",
        "discounts": {},
    },
    {
        "id": "GEFEST-PLATE",
        "name": "GEFEST Плита газовая 3200",
        "description": "",
        "price": 15000.0,
        "stock": 2,
        "unit": "шт",
        "category": "Плиты",
        "supplier_sku": "GEFEST-PLATE",
        "discounts": {},
    },
]


class CatalogTests(unittest.TestCase):
    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_search_keeps_numeric_tokens(self, _mock_load):
        results = search_products("кондер 12")
        self.assertEqual(results[0]["id"], "AC-12")
        self.assertNotIn("AC-09", [item["id"] for item in results])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_render_catalog_context_includes_ids(self, _mock_load):
        context, matches = render_catalog_context("бойлер 80")
        self.assertEqual(matches[0]["id"], "BOILER-80")
        self.assertIn("ID: BOILER-80", context)

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_resolve_product_by_id(self, _mock_load):
        product = resolve_catalog_product(product_id="ac-12")
        self.assertIsNotNone(product)
        self.assertEqual(product["name"], "Dahatsu Кондиционер 12 ONYX")

    def test_price_for_quantity_applies_discount(self):
        unit_price, discount_pct = price_for_quantity(CATALOG_FIXTURE[0], 5)
        self.assertEqual(discount_pct, 7)
        self.assertEqual(unit_price, 23250.0)

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_budget_query_uses_previous_context(self, _mock_load):
        results = search_products("от 5000 до 8000", preferred_product_ids=["BOILER-80", "BOILER-50"])
        self.assertEqual([item["id"] for item in results], ["BOILER-50"])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_budget_and_category_query_filters_products(self, _mock_load):
        results = search_products("есть микроволновка до 4000 руб")
        self.assertEqual([item["id"] for item in results], ["MW-1"])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_appliance_query_skips_accessories(self, _mock_load):
        results = search_products("микроволновка до 4000")
        self.assertEqual(results[0]["id"], "MW-1")
        self.assertNotIn("MW-BRACKET", [item["id"] for item in results])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_numeric_context_stays_inside_previous_category(self, _mock_load):
        results = search_products("35", preferred_product_ids=["AC-35"])
        self.assertEqual([item["id"] for item in results], ["AC-35"])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_latin_brand_does_not_match_longer_words(self, _mock_load):
        results = search_products("Gree")
        self.assertIn("GREE-1", [item["id"] for item in results])
        self.assertNotIn("GREEN-1", [item["id"] for item in results])

    @patch("catalog.load_products", return_value=CATALOG_FIXTURE)
    def test_alternatives_keep_requested_product_type(self, _mock_load):
        results = search_alternatives("вытяжка gefest", limit=3)
        self.assertIn("HOOD-1", [item["id"] for item in results])
        self.assertNotIn("GEFEST-PLATE", [item["id"] for item in results])

    def test_selection_reply_accepts_position_numbers(self):
        reply = build_selection_reply("ставь заказ на 2 позицию из списка", CATALOG_FIXTURE[:3])
        self.assertIn("позицию 2", reply)

    def test_selection_reply_accepts_last_position(self):
        reply = build_selection_reply("нужен последний из списка", CATALOG_FIXTURE[:3])
        self.assertIn(CATALOG_FIXTURE[2]["name"], reply)

    def test_selection_reply_rejects_out_of_range_position(self):
        reply = build_selection_reply("11", CATALOG_FIXTURE[:3])
        self.assertIn("3 позиции", reply)
        self.assertIn("11", reply)

    def test_selection_reply_does_not_steal_product_numbers(self):
        reply = build_selection_reply("кондиционер на 12", CATALOG_FIXTURE)
        self.assertIsNone(reply)

    def test_smalltalk_does_not_trigger_catalog(self):
        self.assertIsNotNone(build_smalltalk_reply("Привет"))
        self.assertIsNotNone(build_smalltalk_reply("Ты поплыл?"))

    def test_selection_reply_uses_context_products(self):
        reply = build_selection_reply("беру первый", CATALOG_FIXTURE[:2])
        self.assertIn("Dahatsu Кондиционер 12 ONYX", reply)

    def test_select_product_from_context_returns_selected_product(self):
        selected = select_product_from_context("беру второй", CATALOG_FIXTURE[:3])
        self.assertIsNotNone(selected)
        index, product = selected
        self.assertEqual(index, 1)
        self.assertEqual(product["id"], "AC-09")

    def test_select_product_from_context_rejects_quantity(self):
        selected = select_product_from_context("1 шт", CATALOG_FIXTURE[:3])
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
