import unittest
from unittest.mock import AsyncMock, patch

import database


class DatabaseLogicTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_order_rejects_invalid_status_transition(self):
        with patch("database.get_order", new=AsyncMock(return_value={"id": "ORD-1", "status": "new"})), patch(
            "database.aiosqlite.connect"
        ) as mock_connect:
            with self.assertRaises(ValueError):
                await database.update_order("ORD-1", {"status": "completed"})
            self.assertFalse(mock_connect.called)


if __name__ == "__main__":
    unittest.main()
