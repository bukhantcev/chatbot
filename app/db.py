import os
from typing import Dict, List

import aiosqlite


MessageRecord = Dict[str, str]


class Database:
    def __init__(self, path: str, default_level: int) -> None:
        self.path = path
        self.default_level = default_level

    async def init(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    telegram_id INTEGER PRIMARY KEY,
                    level INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_user_id
                ON messages(telegram_id, id)
                """
            )
            await db.commit()

    async def get_level(self, telegram_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT level FROM user_settings WHERE telegram_id = ?",
                (telegram_id,),
            )
            row = await cursor.fetchone()

        return int(row[0]) if row else self.default_level

    async def set_level(self, telegram_id: int, level: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO user_settings(telegram_id, level, updated_at)
                VALUES(?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    level = excluded.level,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_id, level),
            )
            await db.commit()

    async def add_message(self, telegram_id: int, role: str, content: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO messages(telegram_id, role, content) VALUES(?, ?, ?)",
                (telegram_id, role, content),
            )
            await db.commit()

    async def get_recent_messages(self, telegram_id: int, limit: int) -> List[MessageRecord]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT role, content
                FROM messages
                WHERE telegram_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (telegram_id, limit),
            )
            rows = await cursor.fetchall()

        return [
            {"role": str(row["role"]), "content": str(row["content"])}
            for row in reversed(rows)
        ]

    async def reset_context(self, telegram_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM messages WHERE telegram_id = ?", (telegram_id,))
            await db.commit()
