import unittest
from unittest.mock import patch, sentinel

import sales_agent


class GroqClientFactoryTests(unittest.TestCase):
    def test_uses_dedicated_http_client_when_proxy_is_configured(self):
        factory = getattr(sales_agent, "_create_groq_client", None)
        self.assertIsNotNone(factory, "Groq client factory is missing")

        with (
            patch.object(
                sales_agent.httpx,
                "AsyncClient",
                return_value=sentinel.http_client,
            ) as async_client,
            patch.object(
                sales_agent,
                "AsyncGroq",
                return_value=sentinel.groq_client,
            ) as async_groq,
        ):
            client = factory("test-key", "socks5://127.0.0.1:11080")

        async_client.assert_called_once_with(proxy="socks5://127.0.0.1:11080")
        async_groq.assert_called_once_with(
            api_key="test-key",
            http_client=sentinel.http_client,
        )
        self.assertIs(client, sentinel.groq_client)

    def test_uses_default_transport_without_proxy(self):
        factory = getattr(sales_agent, "_create_groq_client", None)
        self.assertIsNotNone(factory, "Groq client factory is missing")

        with (
            patch.object(sales_agent.httpx, "AsyncClient") as async_client,
            patch.object(
                sales_agent,
                "AsyncGroq",
                return_value=sentinel.groq_client,
            ) as async_groq,
        ):
            client = factory("test-key", "")

        async_client.assert_not_called()
        async_groq.assert_called_once_with(api_key="test-key")
        self.assertIs(client, sentinel.groq_client)

    def test_sales_agent_uses_configured_proxy(self):
        proxy_url = getattr(sales_agent, "GROQ_PROXY_URL", None)
        self.assertIsNotNone(proxy_url, "GROQ_PROXY_URL is not loaded")

        with (
            patch.object(
                sales_agent,
                "GROQ_PROXY_URL",
                "socks5://127.0.0.1:11080",
            ),
            patch.object(
                sales_agent,
                "_create_groq_client",
                return_value=sentinel.groq_client,
            ) as factory,
            patch.object(sales_agent, "reload_products", return_value=[{}]),
        ):
            agent = sales_agent.SalesAgent()

        factory.assert_called_once_with(
            sales_agent.GROQ_API_KEY,
            "socks5://127.0.0.1:11080",
        )
        self.assertIs(agent._client, sentinel.groq_client)


if __name__ == "__main__":
    unittest.main()
