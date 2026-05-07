# Handoff: БытТехОпт

## Статус проекта

- Код магазина: `C:\Users\user\Documents\GitHub\Codex\Telegram_Sales_meneger\web-store`
- GitHub branch: `codex/Site_master`
- Production URL: `https://climat-simf.ru`
- VPS: `212.116.115.150`
- App path на VPS: `/var/www/climat-simf.ru`
- PM2 process: `climat-simf-store`
- Домен и HTTPS работают через Nginx и Let's Encrypt.
- SSH-ключ для deploy настроен: локальный приватный ключ `C:\Users\user\.ssh\climat_simf_deploy`, публичный ключ добавлен в `/root/.ssh/authorized_keys` на VPS. Для `npm run deploy:vps` можно использовать `WEB_STORE_SSH_KEY_PATH`.

## Что уже сделано

- Развернут интернет-магазин БытТехОпт на Next.js + PostgreSQL + Prisma.
- Подключены каталог, категории, цены, остатки и изображения от I-T-P.
- Загружены метаданные фото: примерно `880351` записей `ProductImage`, около `182062` товаров с фото.
- На странице товара добавлена галерея: основное фото, стрелки, миниатюры и счетчик.
- В карточке товара выводятся реальные доступные характеристики: SKU, категория, бренд, партномер, штрихкоды, гарантия, вес, объем упаковки, кратность заказа, срок поставки.
- Phase A витрины маркетплейса: карточки товара, страница товара, корзина, checkout, страница успешного заказа и Telegram-уведомление теперь используют честную формулировку `В наличии у поставщика` / `Доставка под заказ 7 дней`.
- Характеристики на странице товара выведены табличными строками с нормальными отступами, а покупательский сценарий оформлен как заявка с подтверждением менеджером перед оплатой.
- Phase B первая волна: каталог получил сортировку в URL, быстрые фильтры `В наличии` / `С фото` / `До 10 000 ₽`, активные чипы фильтров, горизонтальные быстрые категории и короткие характеристики внутри карточек товара.
- На странице товара добавлен блок похожих товаров из той же категории и CTA для подбора аналога через менеджера.
- Корзина усилена как заявка: показывает количество товаров, даёт продолжить покупки, очистить корзину и ведёт к оформлению заявки только после успешной проверки состава.
- Phase B карточки стали умнее без нового фида: сайт извлекает очевидные характеристики из названий товаров (`л/сутки`, бак в литрах, диагональ ТВ, 4K, RAM/SSD) и показывает их в карточках каталога и таблице товара.
- SEO/конверсия: добавлены canonical и SEO-шаблоны для каталога/категорий, JSON-LD `Product` и `BreadcrumbList` для карточки товара, быстрый заказ с карточки товара, отдельное Telegram-сообщение `Быстрый заказ`, мобильная sticky-панель покупки.
- Админ-обзор усилен под продажи: очередь действий, последние заявки, быстрые заказы, качество каталога, товары без фото/цены, последние синхронизации.
- Поиск начал собирать популярные запросы в `Setting` без новой миграции; в админке появился блок `Популярные поиски` со ссылками обратно в выдачу.
- Каталог получил первый слой категорийных фильтров по уже извлекаемым характеристикам из названий: производительность `л/сутки`, объем бака, `4K / UHD`, `Full HD`, `SSD`, оперативная память. Фильтры живут в URL как `spec=...`, работают на desktop и mobile, активные фильтры показываются чипами.
- В карточку товара в каталоге добавлен раскрываемый быстрый заказ: клиент может оставить имя и телефон прямо из выдачи, заявка идет тем же server action и Telegram-путем, что и быстрый заказ на странице товара.
- Исправлен null-safe фильтр уценки/б/у товаров: товары с пустым публичным `name` больше не выпадают из sitemap/home/related-выдачи только из-за SQL `NULL` в условии `NOT contains`.
- Заказы стали понятнее для продаж: добавлены русские статусы заявок, цветные бейджи в списке/карточке заказа, быстрый звонок клиенту, план обработки заявки для менеджера и таймлайн `Что дальше` на странице успешной заявки.
- SEO/нагрузка: параметрические URL каталога, фильтров, сортировок, пагинации и поиска теперь получают `noindex, follow`; `robots.txt` закрывает `/search`, админку, API и URL с query-параметрами, чтобы боты меньше грузили бесконечные фильтры.
- Мобильный каталог стал плотнее и быстрее для воронки: липкий блок `Фильтры` / `Категории` с бейджем активных фильтров, горизонтальные быстрые фильтры без переполнения экрана, компактнее карточка товара на телефоне.
- Добавлен безопасный deploy-инструмент `npm run deploy:vps`: собирает архив без `.env`/`.next`/`node_modules`, делает source-backup на VPS, запускает production build, проверяет `.next/prerender-manifest.json` и `.next/BUILD_ID`, перезапускает PM2 и делает healthcheck. После таймаута долгого build ожидание удаленной команды переведено на polling без SSH channel read timeout; добавлен `--remote-timeout`; локальный VPS-healthcheck после PM2 и внешний public healthcheck теперь делают retry, а печать ошибок безопасна для Windows-консоли.
- Зафиксировано ТЗ по фасетным фильтрам в `docs/FACET_FILTERS_TZ.md`; шаг 1 реализует расширенный слой категорийных фильтров без миграции базы: климат, холодильники, телевизоры, компьютеры, стиральные машины, группировка фильтров в UI и совместимый URL `spec=...`.
- Брендовый фильтр усилен до маркетплейсного сценария: вместо одиночного select в каталоге и поиске теперь чекбоксы брендов с несколькими значениями в URL `brand=...&brand=...`, обратная совместимость с одиночным `brand` сохранена.
- Стабилизирован production build на большой базе: главная страница и `sitemap.xml` больше не блокируют `next build` долгими запросами к базе; sitemap генерируется динамически и кэшируется на 1 час через `unstable_cache`.
- Начат шаг 2 по фасетам: добавлена Prisma-модель `ProductAttribute`, чистый extractor атрибутов из названий и команда `npm run sync:attributes` для backfill `source=name`. Извлекаются производительность, объем бака, диагональ ТВ, разрешение, Smart TV, RAM, тип и объем накопителя. `spec`-фильтры для доступных атрибутов уже строят Prisma `where` через `attributes.some`, сохраняя fallback на название/поставщика. Шаг 3 начат и выложен: у `spec`-фильтров появились счетчики, считаются последовательно, чтобы не перегружать Prisma connection pool.
- Если поставщик не дает описание, сайт формирует клиентское автоописание из доступных данных товара.
- Исправлена проблема с падением сайта из-за параллельных `sync:prices`: старый дублирующий cron отключен, синхронизация цен больше не делает тяжелый общий `UPDATE Product ... WHERE 1=1` в начале.
- Добавлен индекс `ProductImage_productId_deleted_priority_idx` для ускорения выдачи первого фото товара.
- Убрана тяжелая сортировка по `images._count`; витрина сортирует через `hasImage`.
- `robots.txt`, `llms.txt`, sitemap и публичные страницы работают.
- Telegram-уведомления о заказах настроены на production: переменные Telegram заполнены в `/var/www/climat-simf.ru/.env`, PM2 перезапущен с `--update-env`.
- Первый тестовый заказ через production `createLocalOrder`: `ORD-20260502-MXK3DM`, уведомление ушло в Telegram-группу.

## Важные ограничения по данным

- В текущем стандартном фиде I-T-P нет полных заводских описаний и расширенных технических характеристик.
- В базе сейчас `description` и `specifications` у массового каталога не заполнены поставщиком.
- Вес, объем, гарантия, партномер, штрихкоды, бренд, кратность и срок поставки есть у значительной части товаров и уже выводятся.
- Для карточек уровня маркетплейса нужен отдельный источник характеристик: дополнительный фид I-T-P, ручное заполнение в админке или отдельное обогащение данных.

## Cron и синхронизации

Активные cron-задачи находятся в root crontab, блок `climat-simf.ru sync jobs`:

- цены: каждые 4 часа
- категории: ежедневно ночью
- товары: ежедневно ночью
- фото: ежедневно, лимит `ITP_IMAGE_SYNC_LIMIT=20000`

Старый `/etc/cron.d/climat-simf` отключен, чтобы не запускать синхронизации дублем.

Логи:

- `/var/log/climat-simf.ru/sync-prices.log`
- `/var/log/climat-simf.ru/sync-categories.log`
- `/var/log/climat-simf.ru/sync-products.log`
- `/var/log/climat-simf.ru/sync-images.log`

## Проверки после последних правок

Локально:

- `npm.cmd test` - 65 tests passed
- `npm.cmd run test:deploy` - passed
- `npm.cmd run lint` - passed
- `npm.cmd run build` - passed
- `http://localhost:50065/catalog?available=1&photo=1` - `200`, HTML содержит мобильные блоки `Фильтры` и `Категории`

На VPS:

- `npm run build` - passed после выкладки Phase A
- `pm2 restart climat-simf-store --update-env` - выполнен
- `https://climat-simf.ru/` - `200`
- Товар `11261200` проверен на проде: страница отдает `200`, содержит `В наличии у поставщика` и `Доставка под заказ 7 дней`, старого текста `день в день` нет.
- Тестовая заявка создана через серверный `createLocalOrder`: `ORD-20260502-ZCO0EA`, 1 товар, сумма `19800`.
- Backup перед выкладкой Phase A: `/var/www/climat-simf.ru.backup-phase-a-20260502151952`
- Phase B первая волна выложена на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `https://climat-simf.ru/` - `200`.
- Продовые smoke-проверки Phase B: `/catalog?available=1&photo=1&sort=price_asc` отдает `200` и показывает сортировку/быстрый фильтр; товар `11261200` отдает `200`, показывает `Похожие товары`, CTA подбора аналога и `Доставка под заказ 7 дней`.
- Backup изменяемых файлов перед выкладкой Phase B: `/var/www/climat-simf.ru.file-backup-phase-b-20260502191400`
- Извлечение характеристик из названий выложено на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed. Smoke: товар `11261200` показывает `Производительность`, `Объем бака`, `30 л/сутки`, `4 л`; каталог по `Ballu Vector BD-30L` показывает `30 л/сутки` и `4 л`.
- Backup изменяемых файлов перед выкладкой extractor: `/var/www/climat-simf.ru.file-backup-spec-extract-20260502192800`
- SEO + быстрый заказ выложены на VPS: product page отдает JSON-LD `Product`, JSON-LD `BreadcrumbList`, canonical и форму `Быстрый заказ`; каталог отдает canonical без параметров фильтрации.
- Тестовый быстрый заказ создан через backend-путь с Telegram-уведомлением: `ORD-20260502-LCT8E5`, SKU `11261200`, сумма `19800`.
- Backup изменяемых файлов перед выкладкой SEO/quick order: `/var/www/climat-simf.ru.file-backup-seo-quick-20260503023700`
- Админ-сводка и популярные поиски выложены на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `/search?q=Ballu%20BD-30L` - `200`, `/admin` - `200`, `Setting.SEARCH_POPULAR_TERMS_V1` записал `ballu bd-30l`.
- Backup изменяемых файлов перед выкладкой админ-сводки/поисковой аналитики: `/var/www/climat-simf.ru.file-backup-admin-dashboard-20260503030611`
- Категорийные spec-фильтры выложены на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `/catalog?spec=tv_4k` - `200`, `/search?q=ssd&spec=storage_ssd` - `200`, в выдаче найден фильтр `4K / UHD`.
- Backup изменяемых файлов перед выкладкой spec-фильтров: `/var/www/climat-simf.ru.file-backup-spec-filters-20260503031851`
- Быстрый заказ из карточки каталога выложен на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, после прогрева `/catalog?available=1&photo=1` - `200`, `/` - `200`, в HTML карточек есть поля quick order (`customerName`, `phone`, `personalDataConsent`).
- Backup изменяемых файлов перед выкладкой быстрого заказа в карточке: `/var/www/climat-simf.ru.file-backup-card-quick-order-20260503110019`
- Null-safe фильтр уценки/б/у выложен на VPS: серверный Prisma smoke `NORMAL_RETAIL_ROWS=5`, `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `/sitemap.xml` - `200`, `/` - `200`, sitemap содержит `700` product URL и `300` category URL.
- Backup изменяемых файлов перед выкладкой null-safe фильтра: `/var/www/climat-simf.ru.file-backup-retail-null-filter-fix-20260507011941`
- Улучшенный сценарий обработки заказов выложен на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `/order-success/<id>` - `200` и содержит `Что дальше` / `Позвонить менеджеру`; `/admin/orders/<id>` с admin-cookie - `200` и содержит `Состав заказа` / `Позвонить`.
- Backup изменяемых файлов перед выкладкой order flow: `/var/www/climat-simf.ru.file-backup-order-flow-20260507013614`
- Noindex для параметрических URL выложен на VPS: `npm run build` - passed, `pm2 restart climat-simf-store --update-env` - passed, `/catalog` - `200` без `noindex`, `/catalog?available=1&photo=1` - `200` с `noindex`, `/search?q=ssd` - `200` с `noindex`; `/robots.txt` - `200`, содержит `Disallow: /*?*` и `Disallow: /search`.
- Backup изменяемых файлов перед выкладкой noindex filtered URLs: `/var/www/climat-simf.ru.file-backup-noindex-filtered-20260507015049`
- Мобильная воронка каталога выложена на VPS: `npm run build` - passed, PM2 перезапущен через `ecosystem.config.cjs`, статус `online`; `https://climat-simf.ru/catalog?available=1&photo=1` - `200`, содержит `Фильтры`, `Категории`, `В наличии` и `noindex`; `/` - `200`; `/robots.txt` - `200`.
- Backup изменяемых файлов перед выкладкой mobile catalog flow: `/var/www/climat-simf.ru.file-backup-mobile-catalog-20260507023146`
- Расширенные фасетные фильтры выложены на VPS после восстановления неполной `.next`: `npm run build` - passed, `.next/BUILD_ID` и `.next/prerender-manifest.json` присутствуют, PM2 `climat-simf-store` - online, локальный healthcheck `127.0.0.1:3001` - ok. Smoke: `/` - `200`, `/catalog?spec=tv_smart` - `200` и содержит `Smart TV` / `Доступно к заказу`, `/catalog?spec=fridge_no_frost` - `200` и содержит `No Frost` / `Доступно к заказу`, `/robots.txt` - `200`.
- Backup source перед попыткой выкладки расширенных фасетных фильтров через deploy helper: `/var/www/climat-simf.ru.source-backup-20260507114907.tar.gz`
- Мультибрендовые фильтры, dynamic home/sitemap и усиленный deploy helper выложены на VPS через `npm run deploy:vps`: `Deploy completed`, `.next/BUILD_ID=BCbJMktk5jh580thUXEdR`, manifest present, PM2 `online`, локальный healthcheck ok. Smoke: `/` - `200`, `/catalog?brand=ATLANT&brand=Indesit` - `200` и содержит `Бренды` / `Бренд:` / `Smart TV`, `/catalog?spec=tv_smart` - `200` и содержит `Smart TV`, `/robots.txt` - `200`, `/sitemap.xml` - `200`.
- Backup source перед контрольной выкладкой multi-brand/deploy helper: `/var/www/climat-simf.ru.source-backup-20260507131125.tar.gz`
- `ProductAttribute` выложен на VPS: `npm run deploy:vps` - `Deploy completed`, затем `npx prisma db push` - schema in sync, `npm run sync:attributes` - `scanned=298688 written=23056`. Распределение атрибутов: `screen_diagonal=9087`, `smart_tv=5572`, `storage_capacity=3231`, `storage_type=3231`, `resolution=1438`, `tank_volume=282`, `ram=166`, `daily_capacity=49`.
- `spec`-фильтры по доступным атрибутам выложены на VPS: `/catalog?spec=tv_smart` - `200`, `/catalog?spec=storage_ssd` - `200`, `/catalog?spec=daily_capacity` - `200`; `.next/BUILD_ID=cplbUwd4FeuKv-ooSsNnQ`, PM2 `online`. Backup source перед выкладкой: `/var/www/climat-simf.ru.source-backup-20260507192503.tar.gz`
- Счетчики `spec`-фильтров выложены на VPS: `npm run deploy:vps` - `Deploy completed`, `/catalog?spec=tv_smart` - `200`, `/catalog?spec=storage_ssd` - `200`, `/catalog?spec=daily_capacity` - `200`, `/sitemap.xml` - `200`; HTML содержит `Smart TV`, разметку счетчика и `Под заказ 7 дней`; `.next/BUILD_ID=Ml8SbNarlXh45R5GiS1V0`, PM2 `online`. Новый хвост PM2-логов после последовательного smoke пустой. Backup source перед выкладкой: `/var/www/climat-simf.ru.source-backup-20260507193902.tar.gz`
- PM2 `climat-simf-store` - online

Предыдущие проверки:

- `npm test -- src/lib/product-display.test.ts` - passed
- `npm run build` - passed
- Проверен товар с `136` фото: страница отдает `200`, галерея подключена, ссылки `/api/product-images/...` присутствуют.

## Что сделать дальше

1. Проверить клиентский путь вручную:
   - открыть `https://climat-simf.ru`
   - выбрать товар
   - проверить галерею фото
   - добавить товар в корзину
   - оформить тестовый заказ

2. Phase B для машины продаж:
   - проверить поведение сортировок и быстрых фильтров на реальных популярных категориях
   - добавить категорийные фильтры по характеристикам там, где данные реально есть: бренд, гарантия, вес/габариты, мощность/тип из отдельного источника
   - доработать карточки под выбранные категории: климат, холодильники, телевизоры, компьютерная техника
   - подготовить админский или полуавтоматический источник расширенных характеристик для важных SKU

3. Решить вопрос с расширенными характеристиками:
   - запросить у I-T-P отдельный фид/метод характеристик, если он доступен
   - или дополнять важные товары вручную через админку
   - или позже сделать отдельный модуль обогащения карточек

## Команда для нового чата

Продолжи проект `БытТехОпт`: прочитай `web-store/HANDOFF.md`, проверь VPS `212.116.115.150`, проверь сайт `https://climat-simf.ru`, PM2 `climat-simf-store`, cron-логи в `/var/log/climat-simf.ru/`, затем продолжай Phase B по каталогу, фильтрам, корзине и расширенным характеристикам.
