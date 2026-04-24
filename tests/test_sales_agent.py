import unittest
from unittest.mock import AsyncMock, patch

from sales_agent import SalesAgent


PRODUCT_FIXTURE = {
    "id": "AC-12",
    "name": "Dahatsu Кондиционер 12 ONYX",
    "description": "",
    "price": 25000.0,
    "stock": 3,
    "unit": "шт",
    "category": "Кондиционеры",
    "supplier_sku": "DH-12-ONYX",
    "discounts": {"5+": 7},
}


class SalesAgentOrderTests(unittest.IsolatedAsyncioTestCase):
    @patch("sales_agent.reload_products", return_value=[PRODUCT_FIXTURE])
    @patch("sales_agent.AsyncGroq")
    async def test_create_order_uses_catalog_price_and_id(self, _mock_groq, _mock_reload):
        agent = SalesAgent()
        with patch("sales_agent.resolve_catalog_product", return_value=PRODUCT_FIXTURE), patch(
            "sales_agent.db_create_order", new=AsyncMock(return_value="ORD-TEST123")
        ) as mock_create:
            result = await agent._create_order(
                {
                    "client_chat_id": 1,
                    "client_name": "Иван",
                    "client_contact": "+79990000000",
                    "product_id": "AC-12",
                    "quantity": 5,
                },
                default_chat_id=1,
            )

        payload = mock_create.await_args.args[0]
        self.assertEqual(payload["product_id"], "AC-12")
        self.assertEqual(payload["product_name"], PRODUCT_FIXTURE["name"])
        self.assertEqual(payload["unit_price"], 23250.0)
        self.assertIn("ORD-TEST123", result)

    @patch("sales_agent.reload_products", return_value=[PRODUCT_FIXTURE])
    @patch("sales_agent.AsyncGroq")
    async def test_create_order_rejects_missing_catalog_product(self, _mock_groq, _mock_reload):
        agent = SalesAgent()
        with patch("sales_agent.resolve_catalog_product", return_value=None):
            result = await agent._create_order(
                {
                    "client_chat_id": 1,
                    "client_name": "Иван",
                    "client_contact": "+79990000000",
                    "product_id": "UNKNOWN",
                    "quantity": 1,
                },
                default_chat_id=1,
            )
        self.assertIn("товар не найден", result.lower())


if __name__ == "__main__":
    unittest.main()
