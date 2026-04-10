import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Groq (FREE — get key at https://console.groq.com, no credit card needed)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Supplier notification channels
SUPPLIER_TELEGRAM_CHAT_ID = os.getenv("SUPPLIER_TELEGRAM_CHAT_ID", "")
SUPPLIER_EMAIL = os.getenv("SUPPLIER_EMAIL", "")

# Supplier REST API — for live stock sync (optional)
SUPPLIER_API_URL = os.getenv("SUPPLIER_API_URL", "")
SUPPLIER_API_KEY = os.getenv("SUPPLIER_API_KEY", "")

# SMTP (optional, used if Telegram supplier notification fails)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Manager identity shown to clients
MANAGER_NAME = os.getenv("MANAGER_NAME", "Алексей")
COMPANY_NAME = os.getenv("COMPANY_NAME", "ТехноТрейд")

# Paths (relative to project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "data", "sales.db")
PRODUCTS_FILE = os.path.join(BASE_DIR, "data", "products.json")

# Conversation history: keep last N messages per client
MAX_HISTORY_MESSAGES = 30
