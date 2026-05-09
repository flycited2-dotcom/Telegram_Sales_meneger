"""Admin-only Telegram training interview helper."""

from __future__ import annotations

import csv
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from config import BASE_DIR


@dataclass(frozen=True)
class TrainingQuestion:
    block: str
    intent: str
    user_phrase: str
    slots: str
    bot_action: str
    bad_reply_guard: str
    topics: tuple[str, ...]


TRAINING_QUESTIONS: tuple[TrainingQuestion, ...] = (
    TrainingQuestion("greeting", "greet", "Привет", "{}", "reply_greeting", "Не предлагать случайный товар", ("greeting",)),
    TrainingQuestion("greeting", "greet", "Здравствуйте", "{}", "reply_greeting", "Не отвечать одинаково на все приветствия", ("greeting",)),
    TrainingQuestion("greeting", "greet", "Добрый день", "{}", "reply_greeting", "Не отвечать одним словом", ("greeting",)),
    TrainingQuestion("greeting", "greet", "Доброго дня", "{}", "reply_greeting", "Не звучать как робот", ("greeting",)),
    TrainingQuestion("greeting", "greet", "Есть кто?", "{}", "reply_greeting", "Не запускать поиск по каталогу", ("greeting",)),
    TrainingQuestion(
        "discovery",
        "find_product",
        "Нужен хороший холодильник",
        "{category: refrigerator}",
        "search_main_products",
        "Не показывать поглотители запаха или аксессуары",
        ("refrigerator", "discovery"),
    ),
    TrainingQuestion(
        "discovery",
        "find_product",
        "Беко есть холодильники?",
        "{category: refrigerator, brand: beko}",
        "normalize_brand_then_search",
        "Не игнорировать кириллицу Беко",
        ("refrigerator", "brand"),
    ),
    TrainingQuestion(
        "discovery",
        "find_product",
        "бе4о есть холодильники?",
        "{category: refrigerator, brand: beko}",
        "normalize_brand_then_search",
        "Не искать по сырой опечатке",
        ("refrigerator", "brand"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Нужен холодильник белый no frost",
        "{category: refrigerator, color: white, feature: no_frost}",
        "search_with_slots",
        "Не показывать не-No-Frost без пометки",
        ("refrigerator", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Кондиционер на 35 квадратов",
        "{category: conditioner, area_m2: 35, btu: 12}",
        "map_area_to_btu_then_search",
        "Не воспринимать 35 как номер позиции",
        ("conditioner", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Кондер нужен 12й инвертор",
        "{category: conditioner, btu: 12, inverter: true}",
        "search_with_required_slots",
        "Не показывать on/off и расходники",
        ("conditioner", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Телевизор 32 диагональ есть?",
        "{category: tv, diagonal: 32}",
        "search_with_slots",
        "Не показывать кронштейны и пульты",
        ("tv", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Чайник до 800 рублей",
        "{category: kettle, price_max: 800}",
        "search_with_price",
        "Не показывать весь каталог",
        ("kettle", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Генератор инверторный до 30000",
        "{category: generator, inverter: true, price_max: 30000}",
        "search_with_required_slots",
        "Не показывать AVR и блоки автопуска",
        ("generator", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Нужен бойлер с сухим тэном",
        "{category: water_heater, heater: dry}",
        "search_with_required_slots",
        "Не показывать бойлеры без сухого тэна",
        ("water_heater", "qualification"),
    ),
    TrainingQuestion(
        "qualification",
        "find_product",
        "Стиралка на 8 кг",
        "{category: washing_machine, load_kg: 8}",
        "search_with_slots",
        "Не воспринимать 8 кг как номер позиции",
        ("washing_machine", "qualification"),
    ),
    TrainingQuestion("listing", "show_results", "Покажи варианты", "{page_size: 5}", "show_first_page", "Не показывать 12-50 позиций сразу", ("listing",)),
    TrainingQuestion("more", "show_more", "Еще", "{}", "show_next_page", "Не начинать новый поиск", ("listing", "more")),
    TrainingQuestion("listing", "ask_recommendation", "А что посоветуешь из этих?", "{}", "recommend_from_last_shown", "Не уходить в новый каталог", ("listing",)),
    TrainingQuestion("selection", "select_position", "3 позицию", "{position: 3}", "select_from_last_shown", "Не выбирать из старого списка", ("selection",)),
    TrainingQuestion("selection", "select_position", "Беру последний", "{position: last}", "select_from_last_shown", "Не запускать новый поиск", ("selection",)),
    TrainingQuestion("selection", "select_position", "Ставь заказ на 12 позицию", "{position: 12}", "select_from_last_shown", "Не выбирать позицию не из последнего списка", ("selection",)),
    TrainingQuestion("checkout", "provide_quantity", "1 шт", "{quantity: 1}", "save_quantity_ask_contact", "Не воспринимать 1 как новый выбор, если товар уже выбран", ("checkout",)),
    TrainingQuestion("checkout", "provide_contact", "897883334455 Петя", "{contact: 897883334455, name: Петя}", "create_order_if_ready", "Не искать товар по телефону", ("checkout",)),
    TrainingQuestion("checkout", "buy_intent", "Меня устраивает генератор за 9000", "{category: generator, price: 9000}", "confirm_product_then_checkout", "Не оформлять без точной позиции", ("checkout", "generator")),
    TrainingQuestion("complaint", "complaint", "Что ты мне шлешь", "{complaint: true}", "apologize_and_recover", "Не выдавать новый каталог", ("complaint",)),
    TrainingQuestion("complaint", "complaint", "Какой топпер, я холодильник заказываю", "{complaint: true, category: refrigerator}", "recover_context", "Не просить модель без исправления ошибки", ("complaint", "refrigerator")),
    TrainingQuestion("greeting", "greet", "Доброе утро", "{}", "reply_greeting", "Не отвечать тем же текстом, что на все приветствия", ("round2", "greeting")),
    TrainingQuestion("greeting", "greet", "Вы работаете?", "{}", "reply_greeting", "Не искать товар по слову работаете", ("round2", "greeting")),
    TrainingQuestion("greeting", "greet", "Можно консультацию?", "{}", "reply_greeting", "Не просить сразу телефон", ("round2", "greeting")),
    TrainingQuestion("discovery", "find_product", "Что есть по холодильникам?", "{category: refrigerator}", "search_main_products", "Не показывать аксессуары и поглотители запаха", ("round2", "refrigerator", "discovery")),
    TrainingQuestion("discovery", "find_product", "Холодильник недорогой нужен", "{category: refrigerator, segment: budget}", "search_main_products", "Не выдавать самый дешевый аксессуар вместо холодильника", ("round2", "refrigerator", "discovery")),
    TrainingQuestion("qualification", "find_product", "Холодильник высокий нужен", "{category: refrigerator, height: tall}", "ask_or_search_height", "Не игнорировать высоту", ("round2", "refrigerator", "qualification")),
    TrainingQuestion("qualification", "find_product", "Холодильник до 25000", "{category: refrigerator, price_max: 25000}", "search_with_price", "Не показывать товары дешевле, но не холодильники", ("round2", "refrigerator", "qualification")),
    TrainingQuestion("qualification", "find_product", "Холодильник серый ноу фрост", "{category: refrigerator, color: gray, feature: no_frost}", "search_with_slots", "Не показывать белые/обычные без пометки", ("round2", "refrigerator", "qualification")),
    TrainingQuestion("qualification", "find_product", "Нужен морозильник", "{category: freezer}", "search_main_products", "Не путать морозильник с холодильником", ("round2", "refrigerator", "freezer")),
    TrainingQuestion("discovery", "find_product", "Есть сплит система?", "{category: conditioner}", "search_main_products", "Не показывать расходники и запчасти", ("round2", "conditioner", "discovery")),
    TrainingQuestion("qualification", "find_product", "Кондиционер 9ка есть?", "{category: conditioner, btu: 9}", "search_with_slots", "Не воспринимать 9 как позицию", ("round2", "conditioner", "qualification")),
    TrainingQuestion("qualification", "find_product", "Кондиционер до 20000", "{category: conditioner, price_max: 20000}", "search_with_price", "Не показывать вентиляторы или аксессуары", ("round2", "conditioner", "qualification")),
    TrainingQuestion("qualification", "find_product", "Нужен кондиционер не инвертор", "{category: conditioner, inverter: false}", "search_with_required_slots", "Не показывать инверторные как основные", ("round2", "conditioner", "qualification")),
    TrainingQuestion("qualification", "find_product", "Нужен инверторный gree 12", "{category: conditioner, brand: gree, btu: 12, inverter: true}", "search_with_required_slots", "Не цеплять green и не показывать другой бренд первым", ("round2", "conditioner", "brand")),
    TrainingQuestion("qualification", "find_product", "На комнату 20 квадратов кондиционер", "{category: conditioner, area_m2: 20, btu: 7}", "map_area_to_btu_then_search", "Не воспринимать 20 как номер позиции", ("round2", "conditioner", "qualification")),
    TrainingQuestion("qualification", "find_product", "На 50 квадратов какой кондиционер?", "{category: conditioner, area_m2: 50, btu: 18}", "map_area_to_btu_then_search", "Не давать случайные 7/9 без уточнения", ("round2", "conditioner", "qualification")),
    TrainingQuestion("discovery", "find_product", "Есть стиральные машинки?", "{category: washing_machine}", "search_main_products", "Не показывать порошки, шланги и аксессуары", ("round2", "washing_machine", "discovery")),
    TrainingQuestion("qualification", "find_product", "Стиралка 6 кг недорогая", "{category: washing_machine, load_kg: 6, segment: budget}", "search_with_slots", "Не воспринимать 6 как позицию", ("round2", "washing_machine", "qualification")),
    TrainingQuestion("qualification", "find_product", "Стиралка узкая нужна", "{category: washing_machine, depth: slim}", "search_with_slots", "Не игнорировать глубину", ("round2", "washing_machine", "qualification")),
    TrainingQuestion("qualification", "find_product", "Стиралка homeline есть?", "{category: washing_machine, brand: homeline}", "normalize_brand_then_search", "Не показывать другие бренды первыми", ("round2", "washing_machine", "brand")),
    TrainingQuestion("discovery", "find_product", "Водонагреватель нужен", "{category: water_heater}", "search_main_products", "Не показывать смесители или комплектующие", ("round2", "water_heater", "discovery")),
    TrainingQuestion("qualification", "find_product", "Бойлер на 80 литров", "{category: water_heater, volume_l: 80}", "search_with_slots", "Не воспринимать 80 как цену или позицию", ("round2", "water_heater", "qualification")),
    TrainingQuestion("qualification", "find_product", "Водонагреватель горизонтальный", "{category: water_heater, mount: horizontal}", "search_with_slots", "Не показывать вертикальные без пометки", ("round2", "water_heater", "qualification")),
    TrainingQuestion("qualification", "find_product", "Бойлер плоский 50 литров", "{category: water_heater, volume_l: 50, form: slim}", "search_with_slots", "Не игнорировать плоский корпус", ("round2", "water_heater", "qualification")),
    TrainingQuestion("discovery", "find_product", "Генератор нужен", "{category: generator}", "search_main_products", "Не показывать AVR и блоки автопуска", ("round2", "generator", "discovery")),
    TrainingQuestion("qualification", "find_product", "Генератор на 3 квт", "{category: generator, power_kw: 3}", "search_with_slots", "Не воспринимать 3 как позицию", ("round2", "generator", "qualification")),
    TrainingQuestion("qualification", "find_product", "Бензиновый генератор с автозапуском", "{category: generator, fuel: gasoline, autostart: true}", "search_with_slots", "Не показывать один блок автозапуска вместо генератора", ("round2", "generator", "qualification")),
    TrainingQuestion("qualification", "find_product", "Генератор закрытого типа", "{category: generator, case: closed}", "search_with_slots", "Не игнорировать закрытый корпус", ("round2", "generator", "qualification")),
    TrainingQuestion("discovery", "find_product", "Микроволновка есть?", "{category: microwave}", "search_main_products", "Не показывать кронштейны и посуду", ("round2", "microwave", "discovery")),
    TrainingQuestion("qualification", "find_product", "Микроволновка до 5000", "{category: microwave, price_max: 5000}", "search_with_price", "Если нет в бюджете, не показывать мусор дешевле", ("round2", "microwave", "qualification")),
    TrainingQuestion("qualification", "find_product", "Микроволновка с грилем", "{category: microwave, grill: true}", "search_with_slots", "Не показывать без гриля как точное совпадение", ("round2", "microwave", "qualification")),
    TrainingQuestion("discovery", "find_product", "Телевизоры есть?", "{category: tv}", "search_main_products", "Не показывать пульты и кронштейны", ("round2", "tv", "discovery")),
    TrainingQuestion("qualification", "find_product", "Телевизор смарт 43", "{category: tv, diagonal: 43, smart: true}", "search_with_slots", "Не воспринимать 43 как позицию", ("round2", "tv", "qualification")),
    TrainingQuestion("qualification", "find_product", "Телевизор до 15000", "{category: tv, price_max: 15000}", "search_with_price", "Не показывать приставки вместо телевизора", ("round2", "tv", "qualification")),
    TrainingQuestion("discovery", "find_product", "Вытяжка нужна", "{category: hood}", "search_main_products", "Не показывать плиту или варочную поверхность", ("round2", "hood", "discovery")),
    TrainingQuestion("qualification", "find_product", "Вытяжка 60 см черная", "{category: hood, width_cm: 60, color: black}", "search_with_slots", "Не игнорировать ширину и цвет", ("round2", "hood", "qualification")),
    TrainingQuestion("qualification", "find_product", "Встраиваемая вытяжка есть?", "{category: hood, type: built_in}", "search_with_slots", "Не показывать купольные как основные", ("round2", "hood", "qualification")),
    TrainingQuestion("qualification", "find_product", "Вытяжка gefest есть?", "{category: hood, brand: gefest}", "search_with_slots_or_alternatives", "Не подменять плитой Gefest", ("round2", "hood", "brand")),
    TrainingQuestion("discovery", "find_product", "Пылесос нужен", "{category: vacuum}", "search_main_products", "Не показывать фильтры и мешки вместо пылесоса", ("round2", "vacuum", "discovery")),
    TrainingQuestion("qualification", "find_product", "Пылесос вертикальный", "{category: vacuum, type: vertical}", "search_with_slots", "Не показывать обычные как точное совпадение", ("round2", "vacuum", "qualification")),
    TrainingQuestion("discovery", "find_product", "Посудомойка есть?", "{category: dishwasher}", "search_main_products", "Не показывать таблетки и аксессуары", ("round2", "dishwasher", "discovery")),
    TrainingQuestion("qualification", "find_product", "Посудомойка 45 см", "{category: dishwasher, width_cm: 45}", "search_with_slots", "Не воспринимать 45 как позицию", ("round2", "dishwasher", "qualification")),
    TrainingQuestion("qualification", "find_product", "Посудомойка встраиваемая", "{category: dishwasher, type: built_in}", "search_with_slots", "Не показывать отдельностоящие без пометки", ("round2", "dishwasher", "qualification")),
    TrainingQuestion("listing", "show_results", "Скинь 3 варианта", "{page_size: 3}", "show_first_page", "Не показывать 12 позиций", ("round2", "listing")),
    TrainingQuestion("listing", "show_results", "Что самое дешевое?", "{sort: price_asc}", "show_cheapest_relevant", "Не показывать дешевый аксессуар вместо товара", ("round2", "listing")),
    TrainingQuestion("listing", "show_results", "Что по качеству лучше?", "{sort: recommended}", "recommend_from_relevant", "Не уходить в общие слова без выбора", ("round2", "listing")),
    TrainingQuestion("listing", "compare_products", "А чем отличаются 1 и 2?", "{compare_positions: [1, 2]}", "compare_last_shown", "Не начинать новый поиск", ("round2", "listing", "selection")),
    TrainingQuestion("more", "show_more", "Давай еще варианты", "{}", "show_next_page", "Не повторять те же позиции", ("round2", "listing", "more")),
    TrainingQuestion("more", "show_more", "А подороже есть?", "{price_direction: higher}", "show_more_or_refine_price", "Не уходить в другую категорию", ("round2", "listing", "more")),
    TrainingQuestion("more", "show_more", "А дешевле?", "{price_direction: lower}", "show_more_or_refine_price", "Не показывать аксессуары как дешевые альтернативы", ("round2", "listing", "more")),
    TrainingQuestion("selection", "select_position", "Вот этот первый", "{position: 1}", "select_from_last_shown", "Не искать по слову первый", ("round2", "selection")),
    TrainingQuestion("selection", "select_position", "Мне второй подходит", "{position: 2}", "select_from_last_shown", "Не запускать новый поиск", ("round2", "selection")),
    TrainingQuestion("selection", "select_position", "Ставь вот этот Beko", "{brand_or_model: beko}", "select_by_model_from_last_shown", "Не выбирать старый Beko вне последнего списка", ("round2", "selection")),
    TrainingQuestion("selection", "ambiguous_selection", "Беру этот", "{ambiguous: true}", "ask_which_position", "Не оформлять без понятной позиции", ("round2", "selection")),
    TrainingQuestion("checkout", "provide_quantity", "Две штуки", "{quantity: 2}", "save_quantity_ask_contact", "Не воспринимать как новый поиск", ("round2", "checkout")),
    TrainingQuestion("checkout", "provide_quantity", "Поставь 3", "{quantity: 3}", "save_quantity_ask_contact", "Не выбирать 3 позицию, если товар уже выбран", ("round2", "checkout")),
    TrainingQuestion("checkout", "provide_contact", "Петя 897883334455", "{name: Петя, contact: 897883334455}", "create_order_if_ready", "Не искать по номеру телефона", ("round2", "checkout")),
    TrainingQuestion("checkout", "provide_contact", "Телефон 897883334455", "{contact: 897883334455}", "save_contact_ask_name", "Не создавать заказ без имени, если имя нужно", ("round2", "checkout")),
    TrainingQuestion("checkout", "provide_name", "Петя", "{name: Петя}", "save_name_ask_missing_contact_or_create", "Не искать товар по имени", ("round2", "checkout")),
    TrainingQuestion("checkout", "change_quantity", "Нет, давай 2 штуки", "{quantity: 2, correction: true}", "update_quantity", "Не создавать второй заказ", ("round2", "checkout")),
    TrainingQuestion("checkout", "cancel_checkout", "Пока не надо, я подумаю", "{cancel_intent: true}", "pause_checkout", "Не давить и не оформлять заказ", ("round2", "checkout")),
    TrainingQuestion("complaint", "complaint", "Ты не слышишь", "{complaint: true}", "apologize_and_recover", "Не выдавать каталог", ("round2", "complaint")),
    TrainingQuestion("complaint", "complaint", "Я просил холодильник, а не аксессуар", "{complaint: true, category: refrigerator}", "recover_context", "Не спорить с клиентом", ("round2", "complaint", "refrigerator")),
    TrainingQuestion("complaint", "complaint", "Это дорого", "{price_objection: true}", "handle_price_objection", "Не спорить и не обесценивать", ("round2", "complaint", "objection")),
    TrainingQuestion("complaint", "complaint", "У конкурентов дешевле", "{price_objection: true, competitor: true}", "handle_price_objection", "Не ругать конкурентов", ("round2", "complaint", "objection")),
    TrainingQuestion("complaint", "complaint", "Мне надо сегодня", "{urgency: today}", "handle_urgency", "Не обещать доставку без данных", ("round2", "complaint", "urgency")),
    TrainingQuestion("no_match", "no_match", "Есть холодильник Samsung?", "{category: refrigerator, brand: samsung}", "safe_no_match_or_alternatives", "Не подменять другим брендом без пояснения", ("round2", "no_match", "refrigerator")),
    TrainingQuestion("no_match", "no_match", "Есть кондиционер за 10000?", "{category: conditioner, price_max: 10000}", "safe_no_match_or_alternatives", "Не показывать нерелевантный товар только из-за цены", ("round2", "no_match", "conditioner")),
    TrainingQuestion("no_match", "no_match", "Нужна конкретно эта модель", "{exact_model_required: true}", "ask_model_or_no_match", "Не подменять модель", ("round2", "no_match")),
)

CSV_FIELDS = [
    "block",
    "intent",
    "user_phrase",
    "slots",
    "bot_action",
    "good_reply",
    "bad_reply_guard",
]


class TrainingBridge:
    def __init__(
        self,
        *,
        csv_path: Optional[str] = None,
        jsonl_path: Optional[str] = None,
        questions: tuple[TrainingQuestion, ...] = TRAINING_QUESTIONS,
    ) -> None:
        self.csv_path = csv_path or os.path.join(BASE_DIR, "data", "sales_training_examples.csv")
        self.jsonl_path = jsonl_path or os.path.join(BASE_DIR, "data", "training_sessions.jsonl")
        self.questions = questions
        self.sessions: dict[int, dict] = {}

    def is_active(self, chat_id: int) -> bool:
        return chat_id in self.sessions

    def topics_text(self) -> str:
        topics = sorted({topic for question in self.questions for topic in question.topics} | {question.block for question in self.questions})
        lines = ["Доступные темы обучения:"]
        for topic in topics:
            count = sum(1 for question in self.questions if topic in question.topics or topic == question.block)
            lines.append(f"/train_start {topic} — {count} вопросов")
        lines.append("/train_start all — все вопросы")
        return "\n".join(lines)

    def start(self, chat_id: int, topic: str = "all") -> str:
        topic = (topic or "all").strip().lower()
        answered_keys = self._answered_question_keys()
        all_topic_indexes = [
            index for index, question in enumerate(self.questions)
            if topic == "all" or topic in question.topics or topic == question.block
        ]
        question_indexes = [
            index for index in all_topic_indexes
            if self._question_key(self.questions[index]) not in answered_keys
        ]
        if not all_topic_indexes:
            return (
                f"Тему '{topic}' не нашел.\n\n"
                + self.topics_text()
            )
        if not question_indexes:
            return (
                f"По теме '{topic}' все вопросы уже есть в CSV.\n"
                "Запустите другую тему или добавьте новые вопросы в training_bridge.py."
            )

        self.sessions[chat_id] = {
            "id": uuid.uuid4().hex[:10],
            "topic": topic,
            "question_indexes": question_indexes,
            "position": 0,
            "answered": 0,
            "skipped_answered": len(all_topic_indexes) - len(question_indexes),
            "topic_total": len(all_topic_indexes),
            "started_at": datetime.now().isoformat(),
        }
        return self._format_current_question(chat_id, intro=True)

    def _answered_question_keys(self) -> set[tuple[str, str, str, str, str]]:
        if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
            return set()
        keys: set[tuple[str, str, str, str, str]] = set()
        with open(self.csv_path, encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                if row.get("good_reply", "").strip():
                    keys.add((
                        row.get("block", ""),
                        row.get("intent", ""),
                        row.get("user_phrase", ""),
                        row.get("slots", ""),
                        row.get("bot_action", ""),
                    ))
        return keys

    def _question_key(self, question: TrainingQuestion) -> tuple[str, str, str, str, str]:
        return (
            question.block,
            question.intent,
            question.user_phrase,
            question.slots,
            question.bot_action,
        )

    def stop(self, chat_id: int) -> str:
        session = self.sessions.pop(chat_id, None)
        if not session:
            return "Активной тренировки нет. Запуск: /train_start"
        return f"Тренировку остановил. Сохранено ответов: {session['answered']}."

    def status(self, chat_id: int) -> str:
        session = self.sessions.get(chat_id)
        if not session:
            return "Активной тренировки нет. Запуск: /train_start или /train_start greeting"
        total = len(session["question_indexes"])
        current = min(session["position"] + 1, total)
        skipped_answered = session.get("skipped_answered", 0)
        topic_total = session.get("topic_total", total)
        return (
            f"Тренировка активна: тема {session['topic']}, непройденный вопрос {current}/{total}, "
            f"сохранено ответов: {session['answered']}.\n"
            f"Уже были в CSV и пропущены: {skipped_answered}/{topic_total}.\n"
            "Ответьте сообщением, /train_skip пропустит вопрос, /train_stop остановит."
        )

    def skip(self, chat_id: int) -> str:
        session = self.sessions.get(chat_id)
        if not session:
            return "Активной тренировки нет. Запуск: /train_start"
        session["position"] += 1
        if session["position"] >= len(session["question_indexes"]):
            answered = session["answered"]
            self.sessions.pop(chat_id, None)
            return f"Тренировка завершена. Сохранено ответов: {answered}."
        return self._format_current_question(chat_id)

    def handle_answer(self, chat_id: int, answer: str, user_name: str = "") -> Optional[str]:
        session = self.sessions.get(chat_id)
        if not session:
            return None

        answer = answer.strip()
        if not answer:
            return "Пустой ответ не сохраняю. Напишите эталонную фразу или /train_skip."

        question = self._current_question(session)
        self._save_answer(chat_id=chat_id, user_name=user_name, session=session, question=question, answer=answer)

        session["answered"] += 1
        session["position"] += 1
        if session["position"] >= len(session["question_indexes"]):
            answered = session["answered"]
            self.sessions.pop(chat_id, None)
            return (
                f"Сохранил ответ. Тренировка завершена: {answered} ответов.\n"
                f"CSV: {self.csv_path}\nJSONL: {self.jsonl_path}"
            )
        return "Сохранил.\n\n" + self._format_current_question(chat_id)

    def _current_question(self, session: dict) -> TrainingQuestion:
        return self.questions[session["question_indexes"][session["position"]]]

    def _format_current_question(self, chat_id: int, *, intro: bool = False) -> str:
        session = self.sessions[chat_id]
        question = self._current_question(session)
        total = len(session["question_indexes"])
        current = session["position"] + 1
        prefix = ""
        if intro:
            skipped_answered = session.get("skipped_answered", 0)
            topic_total = session.get("topic_total", total)
            prefix = (
                "Запускаю тренировку без повторов.\n"
                f"Уже были в CSV и пропущены: {skipped_answered}/{topic_total}.\n\n"
            )
        return (
            f"{prefix}Непройденный вопрос {current}/{total}\n"
            f"Блок: {question.block} / {question.intent}\n"
            f"Клиент пишет: «{question.user_phrase}»\n\n"
            "Ответьте так, как должен ответить сильный менеджер. "
            "Если нужны 2-5 вариантов фразы, разделите их символом |.\n\n"
            f"Что нельзя: {question.bad_reply_guard}\n"
            "Команды: /train_skip, /train_stop, /train_status"
        )

    def _save_answer(
        self,
        *,
        chat_id: int,
        user_name: str,
        session: dict,
        question: TrainingQuestion,
        answer: str,
    ) -> None:
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)

        row = {
            "block": question.block,
            "intent": question.intent,
            "user_phrase": question.user_phrase,
            "slots": question.slots,
            "bot_action": question.bot_action,
            "good_reply": answer,
            "bad_reply_guard": question.bad_reply_guard,
        }
        write_header = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0
        with open(self.csv_path, "a", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

        event = {
            "session_id": session["id"],
            "topic": session["topic"],
            "chat_id": chat_id,
            "user_name": user_name,
            "question_number": session["position"] + 1,
            "saved_at": datetime.now().isoformat(),
            **row,
        }
        with open(self.jsonl_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
