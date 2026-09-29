import os
import aiosqlite
import logging
from datetime import datetime
from typing import List, Dict, Optional

from config import settings
from database.models import (
    CREATE_RATES_HISTORY_TABLE,
    CREATE_SUBSCRIPTIONS_TABLE,
    CREATE_USERS_TABLE,
)

logger = logging.getLogger(__name__)


async def get_db_connection() -> aiosqlite.Connection:
    """Створює та повертає з'єднання з базою даних SQLite."""
    os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
    return await aiosqlite.connect(settings.DB_PATH)


async def init_db() -> None:
    """Ініціалізація баз даних: створення таблиць, очищення дублів та створення унікальних індексів."""
    async with await get_db_connection() as db:
        await db.execute(CREATE_RATES_HISTORY_TABLE)
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.execute(CREATE_USERS_TABLE)

        # Очищення дублікатів в історії курсів (залишаємо тільки запис з максимальним ID)
        delete_duplicates_query = """
        DELETE FROM rates_history
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM rates_history
            GROUP BY date, currency, source
        );
        """
        await db.execute(delete_duplicates_query)

        # Створення унікального індексу для запобігання дублікатам у майбутньому
        create_index_query = """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_rates_history
        ON rates_history(date, currency, source);
        """
        await db.execute(create_index_query)

        await db.commit()
    logger.info("Базу даних та індекси успішно ініціалізовано.")


async def save_rate_history(currency: str, source: str, rate_buy: float, rate_sell: float, date: str) -> None:
    """
    Зберігає запис про курс у базі даних (upsert).
    Якщо запис з такими (date, currency, source) вже існує — оновлює курси.
    """
    async with await get_db_connection() as db:
        query = """
        INSERT INTO rates_history (currency, source, rate_buy, rate_sell, date)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date, currency, source) DO UPDATE SET
            rate_buy = excluded.rate_buy,
            rate_sell = excluded.rate_sell
        """
        await db.execute(query, (currency, source, rate_buy, rate_sell, date))
        await db.commit()


async def get_rate_history(currency: str, days: int = 30, source: str = "nbu") -> List[Dict]:
    """Отримує історію курсів валюти за останні N днів."""
    async with await get_db_connection() as db:
        db.row_factory = aiosqlite.Row
        query = """
        SELECT currency, source, rate_buy, rate_sell, date
        FROM rates_history
        WHERE currency = ? AND source = ?
        ORDER BY date DESC
        LIMIT ?
        """
        async with db.execute(query, (currency, source, days)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_previous_rate(currency: str, before_date: str, source: str = "nbu") -> Optional[float]:
    """
    Отримує останній збережений курс із датою, СТРОГО раніше за before_date (формат YYYY-MM-DD).
    """
    async with await get_db_connection() as db:
        query = """
        SELECT rate_buy
        FROM rates_history
        WHERE currency = ? AND source = ? AND date < ?
        ORDER BY date DESC
        LIMIT 1
        """
        async with db.execute(query, (currency, source, before_date)) as cursor:
            row = await cursor.fetchone()
            if row:
                return float(row[0])
            return None


async def backfill_nbu_history_if_empty() -> None:
    """
    Перевіряє, чи є дані в таблиці rates_history.
    Якщо таблиця порожня — заповнює її даними з НБУ за останні 30 днів.
    """
    async with await get_db_connection() as db:
        async with db.execute("SELECT COUNT(*) FROM rates_history") as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0

    if count == 0:
        logger.info("Таблиця rates_history порожня. Запускаємо backfill курсів НБУ...")
        from services.nbu_api import get_nbu_history_range

        history_data = await get_nbu_history_range(days=30)
        saved_count = 0

        for item in history_data:
            cc = item.get("cc")
            rate = item.get("rate")
            exchangedate = item.get("exchangedate")  # формат "DD.MM.YYYY"

            if cc and rate and exchangedate:
                try:
                    dt = datetime.strptime(exchangedate, "%d.%m.%Y")
                    formatted_date = dt.strftime("%Y-%m-%d")
                    await save_rate_history(
                        currency=cc,
                        source="nbu",
                        rate_buy=float(rate),
                        rate_sell=float(rate),
                        date=formatted_date
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Помилка форматування дати {exchangedate} під час backfill: {e}")

        logger.info(f"Backfill завершено. Записано {saved_count} записів.")


async def add_subscription(user_id: int, currency: str, condition: str, target_rate: float) -> bool:
    """Додає нову підписку користувача, якщо аналогічна не існує."""
    async with await get_db_connection() as db:
        check_query = """
        SELECT id FROM subscriptions
        WHERE user_id = ? AND currency = ? AND condition = ? AND target_rate = ? AND is_active = 1
        """
        async with db.execute(check_query, (user_id, currency, condition, target_rate)) as cursor:
            if await cursor.fetchone():
                return False

        insert_query = """
        INSERT INTO subscriptions (user_id, currency, condition, target_rate)
        VALUES (?, ?, ?, ?)
        """
        await db.execute(insert_query, (user_id, currency, condition, target_rate))
        await db.commit()
        return True


async def get_active_subscriptions() -> List[Dict]:
    """Отримує всі активні підписки."""
    async with await get_db_connection() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM subscriptions WHERE is_active = 1"
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_user_subscriptions(user_id: int) -> List[Dict]:
    """Отримує активні підписки конкретного користувача."""
    async with await get_db_connection() as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1"
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def delete_subscription(sub_id: int, user_id: int) -> bool:
    """Видаляє (деактивує) підписку користувача."""
    async with await get_db_connection() as db:
        query = "UPDATE subscriptions SET is_active = 0 WHERE id = ? AND user_id = ?"
        cursor = await db.execute(query, (sub_id, user_id))
        await db.commit()
        return cursor.rowcount > 0


async def save_user(user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]) -> None:
    """Зберігає або оновлює інформацію про користувача."""
    async with await get_db_connection() as db:
        query = """
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name
        """
        await db.execute(query, (user_id, username, first_name, last_name))
        await db.commit()