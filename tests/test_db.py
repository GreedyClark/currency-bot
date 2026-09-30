import sqlite3

from config import settings
from database.db import add_subscription, save_rate_history, get_previous_rate


async def test_add_subscription_and_duplicate(test_db):
    """Друга ідентична підписка має відхилятись."""
    first = await add_subscription(user_id=1, currency="USD", condition=">", target_rate=42.0)
    second = await add_subscription(user_id=1, currency="USD", condition=">", target_rate=42.0)

    assert first is True
    assert second is False


async def test_save_rate_history_upsert_no_duplicates(test_db):
    """Повторний виклик з тією самою датою оновлює запис, а не створює новий."""
    await save_rate_history("USD", "nbu", 41.0, 41.0, "2026-09-01")
    await save_rate_history("USD", "nbu", 41.5, 41.5, "2026-09-01")

    con = sqlite3.connect(settings.DB_PATH)
    count, max_rate = con.execute(
        "SELECT COUNT(*), MAX(rate_buy) FROM rates_history WHERE currency='USD' AND date='2026-09-01'"
    ).fetchone()
    con.close()

    assert count == 1
    assert max_rate == 41.5


async def test_get_previous_rate_none_when_empty(test_db):
    """Якщо історії немає взагалі — має повернути None, а не помилку."""
    result = await get_previous_rate("EUR", before_date="2026-09-15")
    assert result is None


async def test_get_previous_rate_returns_earlier_value(test_db):
    """Має знайти саме запис СТРОГО раніше за задану дату."""
    await save_rate_history("EUR", "nbu", 45.0, 45.0, "2026-09-10")
    await save_rate_history("EUR", "nbu", 45.5, 45.5, "2026-09-14")

    result = await get_previous_rate("EUR", before_date="2026-09-14")
    assert result == 45.0