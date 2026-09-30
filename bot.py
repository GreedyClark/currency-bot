import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import init_db, backfill_nbu_history_if_empty
from handlers import start, rate, subscribe, history, menu_callbacks, help as help_handler
from services.scheduler import setup_scheduler
from middlewares.throttling import ThrottlingMiddleware

os.makedirs("logs", exist_ok=True)

log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

file_handler = RotatingFileHandler(
    "logs/bot.log",
    maxBytes=5_000_000,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Точка входу для запуску Telegram бота."""
    logger.info("Запуск Currency Bot...")

    await init_db()
    logger.info("Базу даних ініціалізовано.")

    # Автоматично заповнюємо історію курсів за 30 днів, якщо БД порожня
    await backfill_nbu_history_if_empty()

    # Встановлюємо дефолтний HTML parse_mode для всього бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Throttling — захист від спаму командами (не частіше 1 разу на 1.5с)
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=1.5))

    # Реєстрація роутерів
    dp.include_router(start.router)
    dp.include_router(rate.router)
    dp.include_router(subscribe.router)
    dp.include_router(history.router)
    dp.include_router(help_handler.router)
    dp.include_router(menu_callbacks.router)

    # Планувальник задач (підписки та щоденні курси)
    scheduler = setup_scheduler(bot)
    logger.info("Планувальник задач APScheduler запущено.")

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот зупинений.")