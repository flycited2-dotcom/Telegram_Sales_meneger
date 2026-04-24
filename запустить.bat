@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║   Обновление каталога бота           ║
echo  ╚══════════════════════════════════════╝
echo.
echo  Шаг 1: Положите Excel/CSV файлы в папку prices\
echo  Шаг 2: Нажмите любую клавишу для запуска
echo.
pause >nul

echo.
echo  [1/2] Импортирую прайс...
echo  ─────────────────────────────────────────
python import_excel.py
if errorlevel 1 (
    echo.
    echo  ❌ Импорт завершился с ошибкой. Деплой отменён.
    pause
    exit /b 1
)

echo.
echo  [2/2] Заливаю каталог на сервер и перезапускаю бота...
echo  ─────────────────────────────────────────
python deploy_catalog.py
if errorlevel 1 (
    echo.
    echo  ❌ Деплой не удался. Проверьте VPS_HOST/VPS_PASSWORD в .env
    pause
    exit /b 1
)

echo.
pause
