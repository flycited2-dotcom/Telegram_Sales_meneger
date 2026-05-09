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
        ) as mock_create, patch("sales_agent.add_order_event", new=AsyncMock()), patch("sales_agent.upsert_lead", new=AsyncMock()):
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

    @patch("sales_agent.save_conversation_history", new=AsyncMock())
    @patch("sales_agent.get_conversation_history", new=AsyncMock(return_value=[]))
    @patch("sales_agent.get_products_by_ids", return_value=[PRODUCT_FIXTURE])
    @patch(
        "sales_agent.get_lead",
        new=AsyncMock(
            return_value={
                "interested_product_ids": ["OLD-1"],
                "last_shown_product_ids": ["AC-12"],
                "selected_product_id": "",
            }
        ),
    )
    @patch("sales_agent.upsert_lead", new=AsyncMock())
    @patch("sales_agent.reload_products", return_value=[PRODUCT_FIXTURE])
    @patch("sales_agent.AsyncGroq")
    async def test_selection_uses_last_shown_and_saves_selected_product(
        self, _mock_groq, _mock_reload, mock_get_products
    ):
        agent = SalesAgent()

        result = await agent.process_message(1, "беру первый", user_name="Иван")

        mock_get_products.assert_called_once_with(["AC-12"])
        sales_agent_module = __import__("sales_agent")
        sales_agent_module.upsert_lead.assert_awaited_once()
        kwargs = sales_agent_module.upsert_lead.await_args.kwargs
        self.assertEqual(kwargs["selected_product_id"], "AC-12")
        self.assertEqual(kwargs["stage"], "checkout")
        self.assertIn("AC-12", kwargs["interested_product_ids"])
        self.assertIn("Зафиксировал позицию 1", result)


if __name__ == "__main__":
    unittest.main()
