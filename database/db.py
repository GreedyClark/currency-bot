import aiosqlite
import logging
from datetime import datetime
from config import settings
from database.models import CREATE_RATES_HISTORY_TABLE, CREATE_SUBSCRIPTIONS_TABLE

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Створює необхідні таблиці в БД, якщо вони відсутні."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(CREATE_RATES_HISTORY_TABLE)
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.commit()


async def save_rate_history(currency: str, source: str, rate_buy: float, rate_sell: float = None,
                            date_str: str = None) -> None:
    """
    Зберігає значення курсу в БД.
    Якщо date_str передано у форматі DD.MM.YYYY, перетворюємо його на YYYY-MM-DD.
    """
    if date_str and "." in date_str:
        try:
            dt = datetime.strptime(date_str, "%d.%m.%Y")
            formatted_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = datetime.now().strftime("%Y-%m-%d")
    elif date_str:
        formatted_date = date_str
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")

    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO rates_history (currency, source, rate_buy, rate_sell, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (currency.upper(), source.lower(), rate_buy, rate_sell, formatted_date)
        )
        await db.commit()


async def get_rate_history(currency: str, days: int = 7, source: str = "nbu") -> list[dict]:
    """Отримує історію курсів з БД за останні N днів, відсортовану DESC (від нових до старих)."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                """
                SELECT currency, source, rate_buy, rate_sell, date
                FROM rates_history
                WHERE currency = ? AND source = ?
                ORDER BY date DESC, id DESC
                    LIMIT ?
                """,
                (currency.upper(), source.lower(), days)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def backfill_nbu_history_if_empty() -> None:
    """Автоматично заповнює БД історією курсів з API НБУ, якщо БД порожня."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM rates_history") as cursor:
            count = (await cursor.fetchone())[0]

    if count == 0:
        logger.info("База даних порожня. Починаємо автоматичний backfill історії курсів за 30 днів...")
        from services.nbu_api import get_nbu_history_range
        history_items = await get_nbu_history_range(days=30)

        for item in history_items:
            code = item.get("cc")
            rate = item.get("rate")
            exchangedate = item.get("exchangedate")
            if code and rate:
                await save_rate_history(
                    currency=code,
                    source="nbu",
                    rate_buy=float(rate),
                    date_str=exchangedate
                )
        logger.info("Backfill завершено успішно!")


async def add_subscription(user_id: int, currency: str, condition: str, target_rate: float) -> bool:
    """Додає нову підписку. Повертає False, якщо аналогічна підписка вже існує."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        async with db.execute(
                """
                SELECT id
                FROM subscriptions
                WHERE user_id = ?
                  AND currency = ?
                  AND condition = ?
                  AND target_rate = ?
                """,
                (user_id, currency.upper(), condition, target_rate)
        ) as cursor:
            if await cursor.fetchone():
                return False

        await db.execute(
            """
            INSERT INTO subscriptions (user_id, currency, condition, target_rate)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, currency.upper(), condition, target_rate)
        )
        await db.commit()
        return True


async def get_all_subscriptions() -> list[dict]:
    """Отримує список усіх активних підписок."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, user_id, currency, condition, target_rate FROM subscriptions") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def remove_subscription_by_id(sub_id: int) -> None:
    """Видаляє підписку за її ID."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
        await db.commit()


async def remove_subscriptions_by_user(user_id: int) -> int:
    """Видаляє всі підписки користувача та повертає кількість видалених записів."""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount