import csv
import json
import os
import tempfile
import unittest

from training_bridge import TrainingBridge, TrainingQuestion


QUESTIONS = (
    TrainingQuestion(
        block="greeting",
        intent="greet",
        user_phrase="Привет",
        slots="{}",
        bot_action="reply_greeting",
        bad_reply_guard="Не предлагать случайный товар",
        topics=("greeting",),
    ),
    TrainingQuestion(
        block="checkout",
        intent="provide_contact",
        user_phrase="897883334455 Петя",
        slots="{contact: 897883334455, name: Петя}",
        bot_action="create_order_if_ready",
        bad_reply_guard="Не искать товар по телефону",
        topics=("checkout",),
    ),
)


class TrainingBridgeTests(unittest.TestCase):
    def test_inactive_answer_is_ignored(self):
        bridge = TrainingBridge(questions=QUESTIONS)
        self.assertIsNone(bridge.handle_answer(1, "Здравствуйте"))

    def test_start_filters_by_topic(self):
        bridge = TrainingBridge(questions=QUESTIONS)
        reply = bridge.start(1, topic="checkout")
        self.assertIn("897883334455 Петя", reply)
        self.assertIn("Вопрос 1/1", reply)

    def test_topics_text_lists_available_topics(self):
        bridge = TrainingBridge(questions=QUESTIONS)
        text = bridge.topics_text()
        self.assertIn("/train_start greeting", text)
        self.assertIn("/train_start checkout", text)
        self.assertIn("/train_start all", text)

    def test_answer_is_saved_to_csv_and_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = os.path.join(tmp, "training.csv")
            jsonl_path = os.path.join(tmp, "training.jsonl")
            bridge = TrainingBridge(csv_path=csv_path, jsonl_path=jsonl_path, questions=QUESTIONS)

            bridge.start(123, topic="greeting")
            reply = bridge.handle_answer(123, "Здравствуйте. Что подобрать?", user_name="Алексей")

            self.assertIn("Тренировка завершена", reply)
            with open(csv_path, encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]["user_phrase"], "Привет")
            self.assertEqual(rows[0]["good_reply"], "Здравствуйте. Что подобрать?")

            with open(jsonl_path, encoding="utf-8") as file:
                event = json.loads(file.readline())
            self.assertEqual(event["chat_id"], 123)
            self.assertEqual(event["user_name"], "Алексей")
            self.assertEqual(event["block"], "greeting")


if __name__ == "__main__":
    unittest.main()
