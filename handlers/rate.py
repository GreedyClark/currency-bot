from datetime import datetime
from aiogram import Router, types
from aiogram.filters import Command
from services.nbu_api import get_nbu_rates
from database.db import get_previous_rate
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

SUPPORTED_CURRENCIES = ["USD", "EUR", "PLN", "GBP", "CHF"]


async def get_rate_change_indicator(currency: str, current_rate: float, current_date: str) -> str:
    """
    Визначає динаміку зміни курсу порівняно з попереднім збереженим днем у БД.
    `current_date` очікується у форматі 'YYYY-MM-DD' або 'DD.MM.YYYY'.
    """
    if "." in current_date:
        try:
            formatted_date = datetime.strptime(current_date, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            formatted_date = current_date
    else:
        formatted_date = current_date

    prev_rate = await get_previous_rate(currency=currency, before_date=formatted_date, source="nbu")
    if prev_rate is None:
        return ""

    diff = current_rate - prev_rate
    if diff > 0.001:
        return f" 📈 (+{diff:.2f})"
    elif diff < -0.001:
        return f" 📉 ({diff:.2f})"
    return " ➖"


@router.message(Command("rate"))
async def cmd_rate(message: types.Message):
    """Обробка команди /rate."""
    rates = await get_nbu_rates()
    if not rates:
        await message.answer("❌ Не вдалося отримати курси валют від НБУ.")
        return

    text_lines = ["<b>📊 Поточний курс валют (НБУ):</b>\n"]
    for r in rates:
        code = r.get("cc")
        if code in SUPPORTED_CURRENCIES:
            val = r.get("rate", 0.0)
            ex_date = r.get("exchangedate", datetime.now().strftime("%d.%m.%Y"))
            indicator = await get_rate_change_indicator(code, val, ex_date)
            text_lines.append(f"• <b>{code}</b>: <code>{val:.2f}</code> UAH{indicator}")

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Оновити", callback_data="menu_rate")
    builder.button(text="⬅️ Головне меню", callback_data="menu_back")
    builder.adjust(1)

    await message.answer("\n".join(text_lines), reply_markup=builder.as_markup())