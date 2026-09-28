from aiogram import Router, types
from aiogram.filters import Command
from services.nbu_api import get_nbu_rates, get_nbu_rate_by_code
from database.db import get_rate_history

router = Router()


async def get_rate_change_indicator(currency: str, current_rate: float) -> str:
    """
    Порівнює поточний курс із записом за попередню дату та повертає текстовий індикатор.
    """
    history = await get_rate_history(currency=currency, days=10, source="nbu")
    if not history:
        return ""

    prev_rate = None
    latest_date = history[0].get("date")
    for item in history:
        if item.get("date") != latest_date:
            prev_rate = item.get("rate_buy")
            break

    if prev_rate is None and len(history) > 1:
        prev_rate = history[1].get("rate_buy")

    if prev_rate is None:
        return ""

    diff = current_rate - prev_rate
    if diff > 0.001:
        return f" (📈 +{diff:.2f})"
    elif diff < -0.001:
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

    await message.answer("\n".join(text_lines))


@router.message(Command("convert"))
async def cmd_convert(message: types.Message) -> None:
    """
    Пряма команда конвертації: /convert [сума] [валюта]
    Приклад: /convert 100 usd
    """
    if not message.text:
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer(
            "❌ <b>Некоректний формат команди.</b>\n\n"
            "Використовуйте: <code>/convert [сума] [usd/eur]</code>\n"
            "Приклад: <code>/convert 100 usd</code>"
        )
        return

    raw_amount = args[0].replace(",", ".")
    currency = args[1].upper()

    if currency not in ["USD", "EUR"]:
        await message.answer("❌ Конвертація доступна тільки для <b>USD</b> та <b>EUR</b>.")
        return

    try:
        amount = float(raw_amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, вкажіть додатнє число для суми.")
        return

    rate = await get_nbu_rate_by_code(currency)
    if not rate:
        await message.answer("❌ Не вдалося отримати актуальний курс.")
        return

    result = amount * rate
    await message.answer(
        f"💱 <b>Результат конвертації:</b>\n\n"
        f"<code>{amount:,.2f}</code> {currency} = <b><code>{result:,.2f}</code> UAH</b>\n"
        f"<i>(Курс НБУ: <code>{rate:.2f}</code> UAH)</i>"
    )