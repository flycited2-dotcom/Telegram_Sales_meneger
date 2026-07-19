import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import TimedOut

import main


class HandleMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_typing_timeout_does_not_abort_message_processing(self):
        chat_id = 987654321
        update = SimpleNamespace(
            message=SimpleNamespace(
                text="test message",
                reply_text=AsyncMock(),
            ),
            effective_chat=SimpleNamespace(id=chat_id),
            effective_user=SimpleNamespace(
                full_name="Test User",
                first_name="Test",
            ),
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(
                send_chat_action=AsyncMock(side_effect=TimedOut()),
            ),
        )
        process_message = AsyncMock(return_value="test reply")

        with (
            patch.object(main, "_is_supplier", return_value=False),
            patch.object(main.agent, "process_message", process_message),
            self.assertLogs(main.logger, level="WARNING") as logs,
        ):
            await main.handle_message(update, context)

        process_message.assert_awaited_once_with(
            chat_id=chat_id,
            text="test message",
            user_name="Test User",
        )
        update.message.reply_text.assert_awaited_once_with("test reply")
        self.assertIn("Could not send typing indicator", "\n".join(logs.output))


class LoggingConfigurationTests(unittest.TestCase):
    def test_httpx_info_logs_are_disabled_to_protect_bot_credentials(self):
        self.assertGreaterEqual(logging.getLogger("httpx").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
