"""Async SQLite layer for orders, leads, conversation history, and catalog cache."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Optional

import aiosqlite

from config import DATABASE_PATH, MAX_HISTORY_MESSAGES_DB, PRODUCTS_FILE

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id                 TEXT PRIMARY KEY,
    client_chat_id     INTEGER NOT NULL,
    client_name        TEXT,
    client_contact     TEXT,
    product_id         TEXT,
    product_name       TEXT NOT NULL,
    quantity           INTEGER NOT NULL,
    unit_price         REAL NOT NULL,
    total_price        REAL NOT NULL,
    status             TEXT NOT NULL DEFAULT 'new',
    notes              TEXT,
    supplier_notified  INTEGER NOT NULL DEFAULT 0,
    supplier_confirmed INTEGER NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    chat_id      INTEGER PRIMARY KEY,
    history      TEXT NOT NULL DEFAULT '[]',
    client_name  TEXT,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    chat_id                INTEGER PRIMARY KEY,
    client_name            TEXT,
    client_contact         TEXT,
    stage                  TEXT NOT NULL DEFAULT 'new',
    summary                TEXT NOT NULL DEFAULT '',
    interested_product_ids TEXT NOT NULL DEFAULT '[]',
    last_message           TEXT NOT NULL DEFAULT '',
    order_count            INTEGER NOT NULL DEFAULT 0,
    total_revenue          REAL NOT NULL DEFAULT 0,
    updated_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source     TEXT NOT NULL,
    payload    TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

_ALLOWED_ORDER_COLS = {"status", "notes", "supplier_notified", "supplier_confirmed"}
_ALLOWED_STATUS_TRANSITIONS = {
    "new": {"confirmed", "reserved", "cancelled"},
    "confirmed": {"reserved", "shipped", "completed", "cancelled"},
    "reserved": {"shipped", "completed", "cancelled"},
    "shipped": {"completed"},
    "completed": set(),
    "cancelled": set(),
}

_catalog_cache: Optional[list] = None


async def init_db() -> None:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()
    logger.info("Database initialized at %s", DATABASE_PATH)


async def get_conversation_history(chat_id: int) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT history FROM conversations WHERE chat_id = ?",
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
            return json.loads(row[0]) if row else []


async def save_conversation_history(
    chat_id: int, history: list, client_name: Optional[str] = None
) -> None:
    if len(history) > MAX_HISTORY_MESSAGES_DB:
        history = history[-MAX_HISTORY_MESSAGES_DB:]

    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO conversations (chat_id, history, client_name, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                history = excluded.history,
                client_name = COALESCE(excluded.client_name, client_name),
                updated_at = excluded.updated_at
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


async def create_order(data: dict) -> str:
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now().isoformat()
    total = data["unit_price"] * data["quantity"]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO orders (
                id, client_chat_id, client_name, client_contact,
                product_id, product_name, quantity, unit_price, total_price,
                status, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_order(order_id: str, updates: dict) -> None:
    invalid = set(updates.keys()) - _ALLOWED_ORDER_COLS
    if invalid:
        raise ValueError(f"Invalid order update fields: {invalid}")

    if "status" in updates:
        order = await get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        current = order["status"]
        target = updates["status"]
        if current != target and target not in _ALLOWED_STATUS_TRANSITIONS.get(current, set()):
            raise ValueError(f"Invalid status transition: {current} -> {target}")

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [order_id]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
        await db.commit()


async def add_order_event(order_id: str, event_type: str, source: str, payload: str = "") -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO order_events (order_id, event_type, source, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, event_type, source, payload, now),
        )
        await db.commit()


async def get_order_events(order_id: str) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM order_events WHERE order_id = ? ORDER BY created_at ASC",
            (order_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_client_orders(client_chat_id: int, active_only: bool = True) -> list:
    query = "SELECT * FROM orders WHERE client_chat_id = ?"
    params: list = [client_chat_id]
    if active_only:
        query += " AND status NOT IN ('completed', 'cancelled')"
    query += " ORDER BY created_at DESC"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def get_lead(chat_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM leads WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            lead = dict(row)
            lead["interested_product_ids"] = json.loads(lead.get("interested_product_ids", "[]"))
            return lead


async def upsert_lead(
    chat_id: int,
    *,
    client_name: Optional[str] = None,
    client_contact: Optional[str] = None,
    stage: Optional[str] = None,
    summary: Optional[str] = None,
    interested_product_ids: Optional[list[str]] = None,
    last_message: Optional[str] = None,
    order_delta: int = 0,
    revenue_delta: float = 0.0,
) -> None:
    existing = await get_lead(chat_id)
    now = datetime.now().isoformat()

    current_products = existing.get("interested_product_ids", []) if existing else []
    merged_products = current_products
    if interested_product_ids:
        merged_products = list(dict.fromkeys(current_products + interested_product_ids))[:12]

    values = {
        "chat_id": chat_id,
        "client_name": client_name or (existing.get("client_name") if existing else None),
        "client_contact": client_contact or (existing.get("client_contact") if existing else None),
        "stage": stage or (existing.get("stage") if existing else "new"),
        "summary": summary if summary is not None else (existing.get("summary") if existing else ""),
        "interested_product_ids": json.dumps(merged_products, ensure_ascii=False),
        "last_message": last_message if last_message is not None else (existing.get("last_message") if existing else ""),
        "order_count": (existing.get("order_count", 0) if existing else 0) + order_delta,
        "total_revenue": (existing.get("total_revenue", 0.0) if existing else 0.0) + revenue_delta,
        "updated_at": now,
    }

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO leads (
                chat_id, client_name, client_contact, stage, summary,
                interested_product_ids, last_message, order_count, total_revenue, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                client_name = excluded.client_name,
                client_contact = excluded.client_contact,
                stage = excluded.stage,
                summary = excluded.summary,
                interested_product_ids = excluded.interested_product_ids,
                last_message = excluded.last_message,
                order_count = excluded.order_count,
                total_revenue = excluded.total_revenue,
                updated_at = excluded.updated_at
            """,
            (
                values["chat_id"],
                values["client_name"],
                values["client_contact"],
                values["stage"],
                values["summary"],
                values["interested_product_ids"],
                values["last_message"],
                values["order_count"],
                values["total_revenue"],
                values["updated_at"],
            ),
        )
        await db.commit()


async def get_order_summary_for_client(chat_id: int) -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            """
            SELECT COUNT(*) AS total_orders, COALESCE(SUM(total_price), 0) AS total_revenue
            FROM orders
            WHERE client_chat_id = ?
            """,
            (chat_id,),
        ) as cur:
            row = await cur.fetchone()
            return {
                "total_orders": row[0] if row else 0,
                "total_revenue": row[1] if row else 0,
            }


async def list_recent_leads(limit: int = 20) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM leads
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for row in rows:
                lead = dict(row)
                lead["interested_product_ids"] = json.loads(lead.get("interested_product_ids", "[]"))
                result.append(lead)
            return result


async def search_leads(query: str, limit: int = 20) -> list:
    pattern = f"%{query}%"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT *
            FROM leads
            WHERE CAST(chat_id AS TEXT) LIKE ?
               OR COALESCE(client_name, '') LIKE ?
               OR COALESCE(client_contact, '') LIKE ?
               OR COALESCE(summary, '') LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (pattern, pattern, pattern, pattern, limit),
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for row in rows:
                lead = dict(row)
                lead["interested_product_ids"] = json.loads(lead.get("interested_product_ids", "[]"))
                result.append(lead)
            return result


def reload_products() -> list:
    global _catalog_cache
    _catalog_cache = None
    return load_products()


def load_products() -> list:
    global _catalog_cache
    if _catalog_cache is None:
        try:
            with open(PRODUCTS_FILE, encoding="utf-8") as file:
                _catalog_cache = json.load(file).get("products", [])
            logger.info("Loaded %d products from catalog", len(_catalog_cache))
        except FileNotFoundError:
            logger.warning("Products file not found: %s", PRODUCTS_FILE)
            _catalog_cache = []
    return _catalog_cache
