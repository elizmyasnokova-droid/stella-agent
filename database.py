"""
Database — профили, натальные карты, история чтений.
"""
import json
import aiosqlite
from datetime import datetime
from typing import Optional
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                first_name    TEXT,
                birth_date    TEXT,
                birth_time    TEXT,
                birth_city    TEXT,
                birth_lat     REAL,
                birth_lon     REAL,
                sun_sign      TEXT,
                moon_sign     TEXT,
                rising_sign   TEXT,
                chinese_sign  TEXT,
                vedic_sign    TEXT,
                life_path     INTEGER,
                created_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS readings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                reading_type TEXT NOT NULL,
                question    TEXT,
                result      TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS compatibility (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                partner_name TEXT,
                partner_sign TEXT,
                partner_birth TEXT,
                result      TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()


# ─── Users ───

async def ensure_user(user_id: int, username: str = None, first_name: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?,?,?)",
            (user_id, username, first_name)
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as c:
            row = await c.fetchone()
    return dict(row) if row else None


async def save_natal_data(user_id: int, **fields):
    allowed = {"birth_date", "birth_time", "birth_city", "birth_lat", "birth_lon",
               "sun_sign", "moon_sign", "rising_sign", "chinese_sign", "vedic_sign", "life_path"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {set_clause} WHERE user_id=?",
            [*updates.values(), user_id]
        )
        await db.commit()


async def get_all_users() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE birth_date IS NOT NULL") as c:
            rows = await c.fetchall()
    return [r[0] for r in rows]


# ─── Readings ───

async def save_reading(user_id: int, reading_type: str, result: str, question: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO readings (user_id, reading_type, question, result) VALUES (?,?,?,?)",
            (user_id, reading_type, question, result)
        )
        await db.commit()
        return cursor.lastrowid


async def get_readings(user_id: int, reading_type: str = None, limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if reading_type:
            async with db.execute(
                "SELECT * FROM readings WHERE user_id=? AND reading_type=? ORDER BY created_at DESC LIMIT ?",
                (user_id, reading_type, limit)
            ) as c:
                rows = await c.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM readings WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ) as c:
                rows = await c.fetchall()
    return [dict(r) for r in rows]


# ─── Compatibility ───

async def save_compatibility(user_id: int, partner_name: str, partner_sign: str,
                              partner_birth: str, result: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO compatibility (user_id, partner_name, partner_sign, partner_birth, result) VALUES (?,?,?,?,?)",
            (user_id, partner_name, partner_sign, partner_birth, result)
        )
        await db.commit()


# ─── Chat history ───

async def get_chat_history(user_id: int, limit: int = 40) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ) as c:
            rows = await c.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def save_message(user_id: int, role: str, content: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?,?,?)",
            (user_id, role, content)
        )
        await db.commit()
