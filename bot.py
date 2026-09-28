import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import init_db
from handlers import start, rate, subscribe, history, menu_callbacks
from services.scheduler import setup_scheduler
from services.api import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def start_fastapi_server() -> None:
    """Запуск FastAPI сервера для Mini App у фоновому режимі."""
    config = uvicorn.Config(
        app=fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    """Точка входу для запуску бота та FastAPI сервера."""
    logger.info("Запуск Currency Bot...")

    await init_db()
    logger.info("Базу даних ініціалізовано.")

    await backfill_nbu_history_if_empty()

    # Встановлюємо дефолтний HTML parse_mode для всього бота
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Реєстрація роутерів
    dp.include_router(start.router)
    dp.include_router(rate.router)
    dp.include_router(subscribe.router)
    dp.include_router(history.router)
    dp.include_router(menu_callbacks.router)

    # Планувальник
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планувальник задач APScheduler запущено.")

    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаємо паралельно бот і FastAPI сервер
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            start_fastapi_server()
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот та сервер зупинені.")