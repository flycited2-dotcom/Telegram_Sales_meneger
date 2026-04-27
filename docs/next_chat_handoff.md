# Next Chat Handoff: Telegram Sales Bot Training

Use this message to continue work in a new chat.

```text
Продолжаем разработку и обучение Telegram sales bot.

Репозиторий:
https://github.com/flycited2-dotcom/Telegram_Sales_meneger

Ветка:
claude/telegram-sales-agent-kGppc

Последний checkpoint commit:
1f0e99077ec34b34d417262d5f0054cc74d6256d

Локальный путь:
C:\Users\user\Documents\GitHub\Codex\Telegram_Sales_meneger

Сервер:
sales_bot_pro уже запущен как systemd service на /root/sales_bot_pro.
Важно: старый бот на сервере не трогать.

Что уже сделано:
- По живым логам нашли главные проблемы: бот путает последний список, аксессуары и основные товары, плохо держит checkout, кириллицу брендов и жалобы.
- Добавлен Telegram training bridge внутри основного бота, без второго polling-процесса.
- Команды обучения в Telegram:
  /train_topics
  /train_start round2
  /train_start greeting
  /train_start refrigerator
  /train_start conditioner
  /train_start checkout
  /train_skip
  /train_status
  /train_stop
- Уже сохранено 29 живых ответов обучения от пользователя.
- В training bridge теперь 97 вопросов, из них 70 новых в round2.
- Сохраненные обучающие ответы лежат в data/sales_training_examples.csv.
- Сырой журнал data/training_sessions.jsonl содержит chat_id, он добавлен в .gitignore и не должен коммититься.

Главные файлы:
- training_bridge.py
- main.py
- catalog.py
- sales_agent.py
- data/sales_training_examples.csv
- docs/sales_bot_training_plan.md
- docs/telegram_training_bridge.md
- docs/next_chat_handoff.md
- tests/test_training_bridge.py
- tests/test_catalog.py

Какой стиль работы нужен:
Использовать karpathy-guidelines всегда: маленькие проверяемые изменения, без лишней архитектурщины, каждый фикс подтверждать тестом или smoke-кейсом.

Что делать дальше:
1. Продолжить обучение через Telegram: пользователь пройдет /train_start round2 или отдельные темы.
2. Считать новые ответы из /root/sales_bot_pro/data/sales_training_examples.csv и /root/sales_bot_pro/data/training_sessions.jsonl.
3. Превратить обучающие ответы в реальные правила:
   - вариативные приветствия;
   - короткий человеческий стиль менеджера;
   - правила уточняющих вопросов;
   - ответы на жалобы;
   - сценарии выбора и заказа.
4. Исправить state machine:
   - хранить last_shown_product_ids отдельно от interested_product_ids;
   - хранить selected_product_id;
   - после выбора товара не искать каталог по телефону/имени;
   - checkout должен собирать количество, имя, телефон и создавать заказ;
   - "1 шт" после выбора товара это количество, а не выбор позиции 1;
   - "11 позицию" выбирать только из последнего показанного списка.
5. Исправить поиск:
   - аксессуары не показывать вместо основного товара;
   - бренды кириллица/латиница: Беко/бе4о -> Beko, Гри/Gree, Хомлайн/Homeline;
   - кондиционеры: площадь -> BTU, 20 м2 -> примерно 7/9, 35 м2 -> 12, 50 м2 -> 18;
   - генераторы: не показывать AVR/блоки автопуска вместо генератора;
   - холодильники: не показывать Topperr поглотители запаха.

Нужный первый шаг в новом чате:
Проверь git status, подтяни серверные training-файлы, посмотри последние логи sales_bot_pro и предложи следующий маленький фикс с тестом.
```

