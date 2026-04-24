"""
Заливает data/products.json на VPS и перезапускает бота.

Запуск:
    python deploy_catalog.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

VPS_HOST     = os.getenv("VPS_HOST", "")
VPS_USER     = os.getenv("VPS_USER", "root")
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "")
VPS_BOT_DIR  = os.getenv("VPS_BOT_DIR", "/root/sales_bot")

LOCAL_CATALOG = Path(__file__).parent / "data" / "products.json"
REMOTE_CATALOG = f"{VPS_BOT_DIR}/data/products.json"


def main() -> None:
    if not VPS_HOST or not VPS_PASSWORD:
        print("❌ VPS_HOST и VPS_PASSWORD не заданы в .env")
        sys.exit(1)

    if not LOCAL_CATALOG.exists():
        print(f"❌ Файл не найден: {LOCAL_CATALOG}")
        print("   Сначала запустите импорт прайса.")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("Устанавливаю paramiko...")
        os.system(f"{sys.executable} -m pip install paramiko -q")
        import paramiko

    print(f"\n🔗 Подключаюсь к {VPS_HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)

    # Заливаем products.json
    print(f"📤 Загружаю каталог → {REMOTE_CATALOG}")
    sftp = client.open_sftp()
    sftp.put(str(LOCAL_CATALOG), REMOTE_CATALOG)
    sftp.close()

    # Перезапускаем бота
    print("🔄 Перезапускаю бота...")
    _, out, err = client.exec_command("systemctl restart sales_bot && sleep 2 && systemctl is-active sales_bot")
    status = (out.read() + err.read()).decode("utf-8", errors="replace").strip()

    client.close()

    if status == "active":
        size_kb = LOCAL_CATALOG.stat().st_size // 1024
        print(f"\n✅ Готово!")
        print(f"   Каталог загружен ({size_kb} КБ)")
        print(f"   Бот перезапущен и работает.")
    else:
        print(f"\n⚠️  Бот запущен, но статус: {status}")
        print("   Проверьте: ssh root@{VPS_HOST} journalctl -u sales_bot -n 20")


if __name__ == "__main__":
    main()
