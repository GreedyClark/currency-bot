from aiogram import Router, types
from aiogram.filters import CommandStart, Command

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    """
    Обробник команди /start.
    Надсилає привітальне повідомлення та списки доступних команд.
    """
    welcome_text = (
        f"👋 **Привіт, {message.from_user.first_name if message.from_user else 'користувач'}!**\n\n"
        "Я бот для моніторингу курсів валют. Допоможу тобі завжди бути в курсі актуальних цін на USD та EUR.\n\n"
        "📌 **Основні команди:**\n"
        "• `/rate` — показати поточний курс валют (НБУ та Monobank)\n"
        "• `/convert [сума] [валюта] [в_валюту]` — конвертація (наприклад: `/convert 100 usd uah`)\n"
        "• `/subscribe [валюта] [умова] [значення]` — підписка на курс (наприклад: `/subscribe usd > 41.5`)\n"
        "• `/unsubscribe` — скасувати всі підписки\n"
        "• `/history [валюта] [днів]` — графік зміни курсу (наприклад: `/history usd 7`)\n\n"
        "💡 *Також ти можеш використовувати inline-режим у будь-якому чаті: просто набери `@назва_бота 100 usd`.*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обробник команди /help."""
    await cmd_start(message)