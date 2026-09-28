from aiogram import Router, types
from aiogram.filters import Command
from services.nbu_api import get_nbu_rates
from database.db import get_rate_history

router = Router()


async def get_rate_change_indicator(currency: str, current_rate: float) -> str:
    """
    Порівнює поточний курс із попереднім значенням з історії та повертає текстовий індикатор.
    """
    history = await get_rate_history(currency=currency, days=2, source="nbu")
    # Якщо записів менше ніж 1 або відсутні дані — не показуємо індикатор
    if not history or len(history) < 1:
        return ""

    prev_rate = history[0].get("rate_buy")
    if prev_rate is None:
        return ""

    diff = current_rate - prev_rate
    if diff > 0:
        return f" (📈 +{diff:.2f})"
    elif diff < 0:
        return f" (📉 {diff:.2f})"
    else:
        return " (➖ 0.00)"


@router.message(Command("rate"))
async def cmd_rate(message: types.Message) -> None:
    """Обробник команди /rate."""
    rates = await get_nbu_rates()
    if not rates:
        await message.answer("❌ Не вдалося отримати актуальні курси валют.")
        return

    text_lines = ["<b>📊 Поточний курс валют (НБУ):</b>\n"]

    for r in rates:
        code = r.get("cc")
        if code in ["USD", "EUR"]:
            val = r.get("rate", 0.0)
            indicator = await get_rate_change_indicator(code, val)
            text_lines.append(f"{code}: <b>{val:.2f}</b> UAH{indicator}")

    await message.answer("\n".join(text_lines), parse_mode="HTML")