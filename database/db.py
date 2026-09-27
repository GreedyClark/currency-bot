import os
import aiosqlite
from typing import List, Dict, Any, Optional
from config import settings
from database.models import CREATE_SUBSCRIPTIONS_TABLE, CREATE_RATE_HISTORY_TABLE


async def init_db() -> None:
    """Ініціалізація бази даних: створення директорії та необхідних таблиць."""
    db_dir = os.path.dirname(settings.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.execute(CREATE_RATE_HISTORY_TABLE)
        await db.commit()


# --- CRUD для підписок ---

async def add_subscription(user_id: int, currency: str, condition: str, target_rate: float) -> bool:
    """Додає нову підписку для користувача. Повертає True, якщо успішно."""
    sql = """
    INSERT INTO subscriptions (user_id, currency, condition, target_rate)
    VALUES (?, ?, ?, ?)
    """
    try:
        async with aiosqlite.connect(settings.DB_PATH) as db:
            await db.execute(sql, (user_id, currency.upper(), condition, target_rate))
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        # Підписка вже існує
        return False


async def remove_subscriptions_by_user(user_id: int) -> int:
    """Видаляє всі підписки користувача. Повертає кількість видалених записів."""
    sql = "DELETE FROM subscriptions WHERE user_id = ?"
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(sql, (user_id,))
        await db.commit()
        return cursor.rowcount


async def get_all_subscriptions() -> List[Dict[str, Any]]:
    """Отримує всі активні підписки для перевірки планивальником."""
    sql = "SELECT id, user_id, currency, condition, target_rate FROM subscriptions"
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# --- Робота з історією курсів ---

async def save_rate_history(currency: str, source: str, rate_buy: float, rate_sell: Optional[float] = None, date_str: Optional[str] = None) -> None:
    """Зберігає або оновлює курс валюти за конкретну дату."""
    import datetime
    if not date_str:
        date_str = datetime.date.today().isoformat()

    sql = """
    INSERT INTO rate_history (date, currency, source, rate_buy, rate_sell)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(date, currency, source) DO UPDATE SET
        rate_buy = excluded.rate_buy,
        rate_sell = excluded.rate_sell
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(sql, (date_str, currency.upper(), source.lower(), rate_buy, rate_sell))
        await db.commit()


async def get_rate_history(currency: str, days: int = 7, source: str = "nbu") -> List[Dict[str, Any]]:
    """Отримує історію курсів за останні N днів для побудови графіків."""
    sql = """
    SELECT date, rate_buy, rate_sell 
    FROM rate_history 
    WHERE currency = ? AND source = ?
    ORDER BY date ASC
    LIMIT ?
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, (currency.upper(), source.lower(), days)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]