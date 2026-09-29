import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from services.nbu_api import get_nbu_rates, TARGET_CURRENCIES
from database.db import save_rate_history, get_active_subscriptions, delete_subscription

logger = logging.getLogger(__name__)


async def save_daily_rates_task() -> None:
    """Щоденна задача: зберігає актуальний курс НБУ в БД о 18:00."""
    logger.info("Запуск щоденного збереження курсів НБУ...")
    rates = await get_nbu_rates()
    if not rates:
        logger.error("Не вдалося отримати курси для щоденного збереження.")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    saved_count = 0

    for r in rates:
        cc = r.get("cc")
        if cc in TARGET_CURRENCIES:
            val = float(r.get("rate", 0.0))
            await save_rate_history(
                currency=cc,
                source="nbu",
                rate_buy=val,
                rate_sell=val,
                date=today_str
            )
            saved_count += 1

    logger.info(f"Щоденне збереження курсів завершено. Збережено {saved_count} валют.")


async def check_subscriptions_task(bot) -> None:
    """Щогодинна задача: перевіряє активні підписки та надсилає сповіщення."""
    logger.info("Перевірка активних підписок...")
    subs = await get_active_subscriptions()
    if not subs:
        return

    rates = await get_nbu_rates()
    if not rates:
        return

    rates_dict = {r.get("cc"): float(r.get("rate", 0.0)) for r in rates if r.get("cc")}

    for sub in subs:
        sub_id = sub["id"]
        user_id = sub["user_id"]
        curr = sub["currency"]
        cond = sub["condition"]
        target = sub["target_rate"]

        current_rate = rates_dict.get(curr)
        if not current_rate:
            continue

        triggered = False
        if cond == ">" and current_rate > target:
            triggered = True
        elif cond == "<" and current_rate < target:
            triggered = True

        if triggered:
            msg = (
                f"🔔 <b>Cповіщення про курс!</b>\n\n"
                f"Курс <b>{curr}</b> досяг вашої цілі:\n"
                f"Поточний: <code>{current_rate:.2f}</code> UAH (умова: {cond} <code>{target:.2f}</code> UAH)."
            )
            try:
                await bot.send_message(chat_id=user_id, text=msg)
                await delete_subscription(sub_id, user_id)
                logger.info(f"Сповіщення надіслано користувачу {user_id}, підписку {sub_id} деактивовано.")
            except Exception as e:
                logger.error(f"Помилка надсилання сповіщення користувачу {user_id}: {e}")


def setup_scheduler(bot) -> AsyncIOScheduler:
    """Налаштування та запуск планувальника задач APScheduler."""
    scheduler = AsyncIOScheduler()

    # Щоденне збереження курсів о 18:00
    scheduler.add_job(
        save_daily_rates_task,
        trigger="cron",
        hour=18,
        minute=0
    )

    # Перевірка підписок щогодини
    scheduler.add_job(
        check_subscriptions_task,
        trigger="cron",
        minute=0,
        args=[bot]
    )

    scheduler.start()
    return scheduler