import operator
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.db import save_rate_history, get_all_subscriptions
from services.nbu_api import get_nbu_rate_by_code, get_nbu_rates

# Словник для безпечного порівняння значень у підписках
OPERATORS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}


async def check_subscriptions_task(bot: Bot) -> None:
    """
    Пеperiodична задача: перевіряє курси та надсилає сповіщення користувачам,
    якщо виконується умова підписки.
    """
    subscriptions = await get_all_subscriptions()
    if not subscriptions:
        return

    for sub in subscriptions:
        rate = await get_nbu_rate_by_code(sub["currency"])
        if rate is None:
            continue

        op_func = OPERATORS.get(sub["condition"])
        if op_func and op_func(rate, sub["target_rate"]):
            text = (
                f"🚨 **Сповіщення про курс {sub['currency']}!**\n\n"
                f"Поточний курс НБУ: **{rate:.2f} UAH**\n"
                f"Твоя умова: `{sub['currency']} {sub['condition']} {sub['target_rate']}`"
            )
            try:
                await bot.send_message(chat_id=sub["user_id"], text=text, parse_mode="Markdown")
            except Exception:
                # Обробка випадків, коли користувач заблокував бота
                pass


async def save_daily_rates_task() -> None:
    """
    Пеperiodична задача: зберігає актуальні курси НБУ в БД для формування історії.
    """
    rates = await get_nbu_rates()
    for rate in rates:
        code = rate.get("cc")
        value = rate.get("rate")
        if code in ["USD", "EUR"] and value:
            await save_rate_history(currency=code, source="nbu", rate_buy=float(value))


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Ініціалізує та налаштовує розклад задач APScheduler.
    """
    scheduler = AsyncIOScheduler()

    # Перевірка підписок щогодини
    scheduler.add_job(check_subscriptions_task, "interval", hours=1, args=[bot])

    # Збереження історії курсів щодня о 18:00
    scheduler.add_job(save_daily_rates_task, "cron", hour=18, minute=0)

    return scheduler