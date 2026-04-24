import unittest
from types import SimpleNamespace

import main


class MainAdminTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_only_blocks_non_admin(self):
        message = SimpleNamespace(reply_text=self._capture)
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=1),
            effective_user=SimpleNamespace(id=1),
            message=message,
        )
        original = main.ADMIN_CHAT_IDS
        main.ADMIN_CHAT_IDS = {999}
        try:
            allowed = await main._admin_only(update)
        finally:
            main.ADMIN_CHAT_IDS = original
        self.assertFalse(allowed)
        self.assertIn("администратору", self.last_reply.lower())

    async def _capture(self, text):
        self.last_reply = text


if __name__ == "__main__":
    unittest.main()
