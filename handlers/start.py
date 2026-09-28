import os
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def get_main_menu_keyboard() -> types.InlineKeyboardMarkup:
    """Генерує клавіатуру головного меню."""
    builder = InlineKeyboardBuilder()

    webapp_url = os.getenv("WEBAPP_URL", "").strip()
    # Показуємо WebApp кнопку тільки якщо є дійсний HTTPS URL (не localhost)
    if webapp_url and webapp_url.startswith("https://") and "localhost" not in webapp_url:
        builder.button(text="🌐 Відкрити Mini App", web_app=WebAppInfo(url=webapp_url))

    builder.button(text="💱 Курс валют", callback_data="menu_rate")
    builder.button(text="🔄 Конвертер", callback_data="menu_convert")
    builder.button(text="🔔 Мої підписки", callback_data="menu_subscribe")
    builder.button(text="📊 Історія курсу", callback_data="menu_history")
    builder.adjust(1 if (webapp_url and webapp_url.startswith("https://") and "localhost" not in webapp_url) else 2, 2)
    return builder.as_markup()


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: types.Message) -> None:
    """Обробник команд /start та /menu."""
    welcome_text = (
        "<b>Вітаю у Currency Bot!</b> 👋\n\n"
        "Оберіть потрібний розділ за допомогою кнопок нижче:"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())