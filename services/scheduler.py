import logging
import operator
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.db import save_rate_history, get_all_subscriptions, remove_subscription_by_id
from services.nbu_api import get_nbu_rates

logger = logging.getLogger(__name__)

OPERATORS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}


async def check_subscriptions_task(bot: Bot) -> None:
    """
    Періодична задача: отримує актуальні курси один раз
    та перевіряє всі активні підписки користувачів.
    """
    subscriptions = await get_all_subscriptions()
    if not subscriptions:
        return

    # Запитуємо курси НБУ 1 раз для всіх підписок
    rates_list = await get_nbu_rates()
    if not rates_list:
        logger.warning("Не вдалося отримати курси НБУ для перевірки підписок.")
        return

    # Формуємо зручний словник: {"USD": 41.50, "EUR": 45.20}
    rates = {r.get("cc"): r.get("rate") for r in rates_list if r.get("cc") and r.get("rate")}

    for sub in subscriptions:
        curr = sub["currency"]
        current_rate = rates.get(curr)
        if current_rate is None:
            continue

        target_rate = sub["target_rate"]
        condition = sub["condition"]
        op_func = OPERATORS.get(condition)

        if op_func and op_func(current_rate, target_rate):
            msg = (
                f"🚨 <b>Сповіщення про курс {curr}!</b>\n\n"
                f"Поточний курс НБУ: <b><code>{current_rate:.2f}</code> UAH</b>\n"
                f"Твоя умова: <code>{curr} {condition} {target_rate:.2f}</code>"
            )

            try:
                await bot.send_message(chat_id=sub["user_id"], text=msg)
                await remove_subscription_by_id(sub["id"])
                logger.info(f"Сповіщення для sub_id={sub['id']} успішно надіслано та видалено.")
            except (TelegramForbiddenError, TelegramBadRequest) as e:
                # Якщо користувач заблокував бота або чат не існує — видаляємо підписку
                logger.warning(f"Неможливо надіслати сповіщення користувачу {sub['user_id']}: {e}. Видаляємо підписку.")
                await remove_subscription_by_id(sub["id"])
            except Exception as e:
                logger.error(f"Помилка при відправці сповіщення для sub_id={sub['id']}: {e}")


async def save_daily_rates_task() -> None:
    """
    Періодична задача: зберігає актуальні курси НБУ в БД для формування історії.
    """
    rates = await get_nbu_rates()
    if not rates:
        return

    for rate in rates:
        code = rate.get("cc")
        value = rate.get("rate")
        exchangedate = rate.get("exchangedate")  # Використовуємо офіційну дату з API НБУ
        if code in ["USD", "EUR"] and value:
            await save_rate_history(
                currency=code,
                source="nbu",
                rate_buy=float(value),
                date_str=exchangedate
            )


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Ініціалізує та налаштовує розклад задач APScheduler.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_subscriptions_task, "interval", hours=1, args=[bot])
    scheduler.add_job(save_daily_rates_task, "cron", hour=18, minute=0)
    return scheduler