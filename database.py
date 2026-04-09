"""Async SQLite layer: orders, conversation history, and product catalog."""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import aiosqlite

from config import DATABASE_PATH, MAX_HISTORY_MESSAGES, PRODUCTS_FILE

logger = logging.getLogger(__name__)

# ─── Schema ───────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id               TEXT PRIMARY KEY,
    client_chat_id   INTEGER NOT NULL,
    client_name      TEXT,
    client_contact   TEXT,
    product_id       TEXT,
    product_name     TEXT NOT NULL,
    quantity         INTEGER NOT NULL,
    unit_price       REAL NOT NULL,
    total_price      REAL NOT NULL,
    status           TEXT NOT NULL DEFAULT 'new',
    notes            TEXT,
    supplier_notified INTEGER NOT NULL DEFAULT 0,
    supplier_confirmed INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    chat_id      INTEGER PRIMARY KEY,
    history      TEXT    NOT NULL DEFAULT '[]',
    client_name  TEXT,
    updated_at   TEXT    NOT NULL
);
"""


async def init_db() -> None:
    """Create tables if they don't exist."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Database initialised at %s", DATABASE_PATH)


# ─── Conversation history ──────────────────────────────────────────────────────

async def get_conversation_history(chat_id: int) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT history FROM conversations WHERE chat_id = ?", (chat_id,)
        ) as cur:
            row = await cur.fetchone()
            return json.loads(row[0]) if row else []


async def save_conversation_history(
    chat_id: int, history: list, client_name: Optional[str] = None
) -> None:
    # Trim to last N messages
    if len(history) > MAX_HISTORY_MESSAGES:
        history = history[-MAX_HISTORY_MESSAGES:]

    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO conversations (chat_id, history, client_name, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                history     = excluded.history,
                client_name = COALESCE(excluded.client_name, client_name),
                updated_at  = excluded.updated_at
            """,
            (chat_id, json.dumps(history, ensure_ascii=False), client_name, now),
        )
        await db.commit()


async def clear_conversation_history(chat_id: int) -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE conversations SET history = '[]', updated_at = ? WHERE chat_id = ?",
            (datetime.now().isoformat(), chat_id),
        )
        await db.commit()


# ─── Orders ───────────────────────────────────────────────────────────────────

async def create_order(data: dict) -> str:
    """Insert a new order and return its generated ID."""
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now().isoformat()
    total = data["unit_price"] * data["quantity"]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO orders
                (id, client_chat_id, client_name, client_contact,
                 product_id, product_name, quantity, unit_price, total_price,
                 status, notes, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_id,
                data["client_chat_id"],
                data.get("client_name"),
                data.get("client_contact", ""),
                data.get("product_id", ""),
                data["product_name"],
                data["quantity"],
                data["unit_price"],
                total,
                "new",
                data.get("notes", ""),
                now,
                now,
            ),
        )
        await db.commit()

    logger.info("Order created: %s", order_id)
    return order_id


async def get_order(order_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_order(order_id: str, updates: dict) -> None:
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [order_id]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            f"UPDATE orders SET {set_clause} WHERE id = ?", values
        )
        await db.commit()


async def get_client_orders(client_chat_id: int, active_only: bool = True) -> list:
    query = "SELECT * FROM orders WHERE client_chat_id = ?"
    params: list = [client_chat_id]
    if active_only:
        query += " AND status NOT IN ('completed','cancelled')"
    query += " ORDER BY created_at DESC"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ─── Product catalog (sync JSON, cached) ──────────────────────────────────────

_catalog_cache: Optional[list] = None


def load_products() -> list:
    """Load products from JSON file (cached in memory)."""
    global _catalog_cache
    if _catalog_cache is None:
        try:
            with open(PRODUCTS_FILE, encoding="utf-8") as f:
                _catalog_cache = json.load(f).get("products", [])
            logger.info("Loaded %d products from catalog", len(_catalog_cache))
        except FileNotFoundError:
            logger.warning("Products file not found: %s", PRODUCTS_FILE)
            _catalog_cache = []
    return _catalog_cache
