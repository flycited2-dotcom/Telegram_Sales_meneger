@echo off
chcp 65001 >nul
echo.
echo  Импорт прайса в каталог бота
echo  ─────────────────────────────
echo  Положите Excel/CSV файлы в папку prices\ и нажмите Enter
echo.
pause

python import_excel.py

echo.
echo  Готово! Напишите боту /reload чтобы обновить каталог.
echo.
pause
