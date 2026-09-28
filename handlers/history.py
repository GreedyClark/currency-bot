import io
import logging
from datetime import datetime
import matplotlib

matplotlib.use('Agg')  # Використовуємо фоновий бекенд без GUI
import matplotlib.pyplot as plt

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from database.db import get_rate_history

logger = logging.getLogger(__name__)
router = Router()

SUPPORTED_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}


async def generate_chart(history_data: list, currency_code: str) -> io.BytesIO:
    """
    Генерує стильний лінійний графік історії курсу валюти за допомогою Matplotlib.
    """
    dates = [
        datetime.strptime(item["date"], "%Y-%m-%d").strftime("%d.%m")
        for item in history_data
    ]
    rates = [item["rate_buy"] for item in history_data]

    plt.figure(figsize=(8, 4.5), dpi=120)

    style_to_use = 'seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default'
    plt.style.use(style_to_use)

    plt.plot(dates, rates, marker='o', color='#D92525', linewidth=2.5, markersize=5)
    plt.title(f"Динаміка курсу {currency_code}/UAH (НБУ)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Дата", fontsize=10)
    plt.ylabel("Курс (UAH)", fontsize=10)
    plt.xticks(rotation=45, fontsize=8)
    plt.yticks(fontsize=9)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120)
    plt.close()
    buf.seek(0)
    return buf


@router.message(Command("history"))
async def cmd_history_direct(message: types.Message):
    """
    Пряма команда: /history <валюта> <днів>
    Приклади:
    • /history pln 14
    • /history gbp 30
    """
    args = message.text.split()[1:]
    curr = "USD"
    days = 30

    if len(args) >= 1:
        curr = args[0].upper()
    if len(args) >= 2:
        try:
            days = int(args[1])
        except ValueError:
            pass

    if curr not in SUPPORTED_CURRENCIES:
        await message.answer(f"❌ Валюта <b>{curr}</b> не підтримується. Доступні: USD, EUR, PLN, GBP, CHF.")
        return

    if days not in [7, 14, 30]:
        days = 30

    history_data = await get_rate_history(currency=curr, days=days, source="nbu")
    if not history_data or len(history_data) < 2:
        await message.answer(
            f"ℹ️ Для побудови графіка недостатньо даних у базі для <b>{curr}</b> за останні {days} днів.")
        return

    history_data = list(reversed(history_data))
    chart_buf = await generate_chart(history_data, curr)
    photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{curr}_history.png")

    await message.answer_photo(
        photo=photo,
        caption=f"📈 Динаміка курсу <b>{curr}</b> за останні {len(history_data)} дн."
    )