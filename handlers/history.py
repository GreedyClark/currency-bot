import io
import matplotlib
import matplotlib.pyplot as plt
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database.db import get_rate_history
from services.nbu_api import get_nbu_rate_by_code

# Налаштування matplotlib для роботи без графічного інтерфейсу (headless)
matplotlib.use("Agg")

router = Router()


def generate_chart(history_data: list, currency: str) -> io.BytesIO:
    """Генерує графік зміни курсу валюти в буфер пам'яті."""
    dates = [item["date"] for item in history_data]
    rates = [item["rate_buy"] for item in history_data]

    plt.figure(figsize=(8, 4))
    plt.plot(dates, rates, marker="o", color="#1f77b4", linewidth=2)
    plt.title(f"Динаміка курсу {currency.upper()} (НБУ)", fontsize=14, fontweight="bold")
    plt.xlabel("Дата", fontsize=10)
    plt.ylabel("Курс (UAH)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120)
    plt.close()
    buf.seek(0)
    return buf


@router.message(Command("history"))
async def cmd_history(message: types.Message) -> None:
    """
    Обробник команди /history [валюта] [днів].
    Приклад: /history usd 7
    """
    if not message.text:
        return

    args = message.text.split()[1:]
    currency = args[0].upper() if len(args) > 0 else "USD"
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7

    if currency not in ["USD", "EUR"]:
        await message.answer("❌ Графіки доступні тільки для **USD** та **EUR**.", parse_mode="Markdown")
        return

    history_data = await get_rate_history(currency=currency, days=days, source="nbu")

    if not history_data or len(history_data) < 2:
        await message.answer(
            f"ℹ️ Для побудови графіка недостатньо даних в БД за останні {days} днів.\n"
            f"Дані накопичуються щодня автоматично."
        )
        return

    await message.answer("📊 Генерую графік...")
    chart_buf = generate_chart(history_data, currency)
    photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{currency}_history.png")

    await message.answer_photo(
        photo=photo,
        caption=f"📈 Динаміка курсу **{currency}** за останні {len(history_data)} дн.",
        parse_mode="Markdown"
    )


# --- Inline-режим ---

@router.inline_query()
async def inline_convert(inline_query: InlineQuery) -> None:
    """
    Обробка inline-запитів.
    Формат у чаті: @botname 100 usd
    """
    query = inline_query.query.strip()
    if not query:
        return

    args = query.split()
    if len(args) < 2 or not args[0].replace(".", "", 1).isdigit():
        return

    amount = float(args[0])
    currency = args[1].upper()

    if currency not in ["USD", "EUR"]:
        return

    rate = await get_nbu_rate_by_code(currency)
    if not rate:
        return

    result = amount * rate
    title = f"{amount:,.2f} {currency} = {result:,.2f} UAH"
    description = f"За офіційним курсом НБУ ({rate:.2f} UAH)"

    item = InlineQueryResultArticle(
        id="1",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=f"💱 **Конвертація:**\n{amount:,.2f} {currency} = **{result:,.2f} UAH**\n*(Курс НБУ: {rate:.2f})*",
            parse_mode="Markdown"
        )
    )

    await inline_query.answer(results=[item], cache_time=60)