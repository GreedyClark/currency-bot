import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from database.db import init_db
from handlers import start, rate, subscribe, history
from services.scheduler import setup_scheduler

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Точка входу для запуску бота."""
    logger.info("Запуск бота...")

    # Ініціалізація бази даних (створення таблиць, якщо вони відсутні)
    await init_db()
    logger.info("База даних успішно ініціалізована.")

    # Створення екземплярів бота та диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # Реєстрація роутерів із хендлерами
    dp.include_router(start.router)
    dp.include_router(rate.router)
    dp.include_router(subscribe.router)
    dp.include_router(history.router)

    # Налаштування та запуск розкладу задач
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("Планувальник задач APScheduler запущено.")

    # Запуск процесів обробки повідомлень (видаляємо накопичені вебхуки)
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