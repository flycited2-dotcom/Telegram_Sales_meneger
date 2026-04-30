# Handoff: БытТехОпт

## Статус

- Код магазина: `C:\Users\user\Documents\GitHub\Codex\Telegram_Sales_meneger\web-store`
- GitHub branch: `codex/Site_master`
- Commit: `33cc609 Add B2B ecommerce web store`
- Production URL: `https://climat-simf.ru`
- VPS: `212.116.115.150`, app path `/var/www/climat-simf.ru`
- PM2 process: `climat-simf-store`
- HTTPS включен через Let's Encrypt.

## Данные

- I-T-P авторизация работает. Проблема была в кодировке кириллицы в `.env`; исправлено через UTF-8.
- Полный каталог товаров загружен: `292539`.
- Цены/остатки обновлены: `200101` активный товар из `200377` позиций I-T-P.
- `276` SKU поставщика не нашлись в локальном статическом каталоге; это теперь логируется как успешная синхронизация с пропусками.
- Метаданные изображений загружены: `5225` записей.
- Cron включен в `/etc/cron.d/climat-simf` с `flock`, чтобы долгие синхронизации не запускались параллельно.
- Telegram-переменные еще не настроены.

## Дальше

1. Проверить сайт и админку:
   - `https://climat-simf.ru`
   - `https://climat-simf.ru/admin/login`
2. Настроить Telegram:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_MANAGER_CHAT_ID`
3. После получения Telegram-данных записать их в `/var/www/climat-simf.ru/.env`, перезапустить PM2 и сделать тестовый заказ.
4. По желанию оптимизировать импорт цен на батчи: текущий последовательный импорт работает, но занимает около часа.

## Важная команда для нового чата

Продолжи проект `БытТехОпт`: прочитай `web-store/HANDOFF.md`, проверь VPS `212.116.115.150`, настрой Telegram через `TELEGRAM_BOT_TOKEN` и `TELEGRAM_MANAGER_CHAT_ID`, сделай тестовый заказ и проверь cron-логи.
