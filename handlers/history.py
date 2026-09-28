import io
import asyncio
import matplotlib
import matplotlib.pyplot as plt
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from database.db import get_rate_history
from services.nbu_api import get_nbu_rate_by_code

matplotlib.use("Agg")
router = Router()


def _build_chart_sync(history_data: list, currency: str) -> io.BytesIO:
    """Синхронне створення графіка Matplotlib через об'єкт Figure (без глобального pyplot)."""
    dates = [item["date"] for item in history_data]
    rates = [item["rate_buy"] for item in history_data]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, rates, marker="o", color="#1f77b4", linewidth=2)
    ax.set_title(f"Динаміка курсу {currency.upper()} (НБУ)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Дата", fontsize=10)
    ax.set_ylabel("Курс (UAH)", fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf


async def generate_chart(history_data: list, currency: str) -> io.BytesIO:
    """Асинхронна обгортка для створення графіка в окремому потоці."""
    return await asyncio.to_thread(_build_chart_sync, history_data, currency)


@router.message(Command("history"))
async def cmd_history(message: types.Message) -> None:
    """Обробник команди /history [usd/eur] [днів]."""
    if not message.text:
        return

    args = message.text.split()[1:]
    currency = args[0].upper() if len(args) > 0 else "USD"

    # Валідація кількості днів (від 1 до 90)
    try:
        days = int(args[1]) if len(args) > 1 else 7
        days = max(1, min(days, 90))
    except ValueError:
        days = 7

    if currency not in ["USD", "EUR"]:
        await message.answer("❌ Графіки доступні тільки для <b>USD</b> та <b>EUR</b>.")
        return

    history_data = await get_rate_history(currency=currency, days=days, source="nbu")
    if not history_data or len(history_data) < 2:
        await message.answer(f"ℹ️ Для побудови графіка недостатньо даних в БД за останні {days} днів.")
        return

    history_data = list(reversed(history_data))
    chart_buf = await generate_chart(history_data, currency)
    photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{currency}_history.png")

    await message.answer_photo(
        photo=photo,
        caption=f"📈 Динаміка курсу <b>{currency}</b> за останні {len(history_data)} дн."
    )


@router.inline_query()
async def inline_convert(inline_query: InlineQuery) -> None:
    """Обробка inline-запитів. Формат: @botname 100 usd"""
    query = inline_query.query.strip()
    if not query:
        return

    args = query.split()
    raw_amount = args[0].replace(",", ".")

    # Підтримка як цілих, так і дробових чисел (100 або 100.5 або 100,5)
    try:
        amount = float(raw_amount)
        if amount <= 0:
            return
    except ValueError:
        return

    if len(args) < 2:
        return

    currency = args[1].upper()
    if currency not in ["USD", "EUR"]:
        return

    rate = await get_nbu_rate_by_code(currency)
    if not rate:
        return

    result = amount * rate
    title = f"{amount:,.2f} {currency} = {result:,.2f} UAH"
    description = f"Курс НБУ: {rate:.2f} UAH"

    item = InlineQueryResultArticle(
        id="1",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=(
                f"💱 <b>Конвертація:</b>\n"
                f"<code>{amount:,.2f}</code> {currency} = <b><code>{result:,.2f}</code> UAH</b>\n"
                f"<i>(Курс НБУ: <code>{rate:.2f}</code> UAH)</i>"
            )
        )
    )

    await inline_query.answer(results=[item], cache_time=60)