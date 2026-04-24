"""
Upload data/products.json to a VPS and restart the bot service.

Run:
    python deploy_catalog.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os

VPS_HOST = os.getenv("VPS_HOST", "")
VPS_USER = os.getenv("VPS_USER", "root")
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "")
VPS_BOT_DIR = os.getenv("VPS_BOT_DIR", "/root/sales_bot")

LOCAL_CATALOG = Path(__file__).parent / "data" / "products.json"
REMOTE_CATALOG = f"{VPS_BOT_DIR}/data/products.json"


def main() -> None:
    if not VPS_HOST or not VPS_PASSWORD:
        print("❌ VPS_HOST and VPS_PASSWORD are not set in .env")
        sys.exit(1)

    if not LOCAL_CATALOG.exists():
        print(f"❌ File not found: {LOCAL_CATALOG}")
        print("   Run the price import first.")
        sys.exit(1)

    try:
        import paramiko
    except ImportError:
        print("❌ paramiko is missing. Install requirements.txt and try again.")
        sys.exit(1)

    print(f"\n🔗 Connecting to {VPS_HOST}...")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASSWORD, timeout=15)

    print(f"📤 Uploading catalog → {REMOTE_CATALOG}")
    sftp = client.open_sftp()
    sftp.put(str(LOCAL_CATALOG), REMOTE_CATALOG)
    sftp.close()

    print("🔄 Restarting bot service...")
    _, out, err = client.exec_command(
        "systemctl restart sales_bot && sleep 2 && systemctl is-active sales_bot"
    )
    status = (out.read() + err.read()).decode("utf-8", errors="replace").strip()
    client.close()

    if status == "active":
        size_kb = LOCAL_CATALOG.stat().st_size // 1024
        print("\n✅ Done!")
        print(f"   Catalog uploaded ({size_kb} KB)")
        print("   Bot restarted and is active.")
    else:
        print(f"\n⚠️ Bot restarted, but service status is: {status}")
        print(f"   Check logs: ssh {VPS_USER}@{VPS_HOST} journalctl -u sales_bot -n 20")


if __name__ == "__main__":
    main()
