from aiogram import Router, types
from aiogram.filters import Command
from services.nbu_api import get_nbu_rate_by_code
from services.mono_api import get_mono_rate_by_code

router = Router()


@router.message(Command("rate"))
async def cmd_rate(message: types.Message) -> None:
    """
    Обробник команди /rate.
    Отримує та відображає поточний курс USD і EUR від НБУ та Monobank.
    """
    await message.answer("🔄 Отримую актуальні курси валют...")

    # Отримання даних з НБУ
    usd_nbu = await get_nbu_rate_by_code("USD")
    eur_nbu = await get_nbu_rate_by_code("EUR")

    # Отримання даних з Monobank
    usd_mono = await get_mono_rate_by_code("USD")
    eur_mono = await get_mono_rate_by_code("EUR")

    text = "📊 **Поточні курси валют (до UAH)**\n\n"

    # Форматування даних НБУ
    text += "🏛 **Національний банк України:**\n"
    text += f"• USD: **{usd_nbu:.2f} UAH**\n" if usd_nbu else "• USD: *Недоступно*\n"
    text += f"• EUR: **{eur_nbu:.2f} UAH**\n\n" if eur_nbu else "• EUR: *Недоступно*\n\n"

    # Форматування даних Monobank
    text += "🏦 **Monobank:**\n"
    if usd_mono:
        text += f"• USD: Купівля **{usd_mono['buy']:.2f}** | Продаж **{usd_mono['sell']:.2f} UAH**\n"
    else:
        text += "• USD: *Недоступно*\n"

    if eur_mono:
        text += f"• EUR: Купівля **{eur_mono['buy']:.2f}** | Продаж **{eur_mono['sell']:.2f} UAH**\n"
    else:
        text += "• EUR: *Недоступно*\n"

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("convert"))
async def cmd_convert(message: types.Message) -> None:
    """
    Обробник команди /convert [сума] [з_валюти] [в_валюту].
    Приклад: /convert 100 usd uah
    """
    if not message.text:
        return

    args = message.text.split()[1:]

    # Валідація кількості аргументів
    if len(args) != 3:
        await message.answer(
            "❌ **Некоректний формат!**\n\n"
            "Використовуйте: `/convert [сума] [з_валюти] [в_валюту]`\n"
            "Приклад: `/convert 100 usd uah`",
            parse_mode="Markdown"
        )
        return

    amount_str, from_curr, to_curr = args[0], args[1].upper(), args[2].upper()

    # Валідація суми
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Сума має бути додатним числом!")
        return

    # Підтримувані валюти
    supported = ["USD", "EUR", "UAH"]
    if from_curr not in supported or to_curr not in supported:
        await message.answer("❌ Підтримуються тільки валюти: **USD, EUR, UAH**.", parse_mode="Markdown")
        return

    if from_curr == to_curr:
        await message.answer(f"Результат: **{amount:.2f} {to_curr}**", parse_mode="Markdown")
        return

    # Розрахунок через курс НБУ
    rate_from = 1.0 if from_curr == "UAH" else await get_nbu_rate_by_code(from_curr)
    rate_to = 1.0 if to_curr == "UAH" else await get_nbu_rate_by_code(to_curr)

    if not rate_from or not rate_to:
        await message.answer("❌ Не вдалося отримати курс для розрахунку. Спробуйте пізніше.")
        return

    # Конвертація в UAH, а потім у цільову валюту
    amount_in_uah = amount * rate_from
    result = amount_in_uah / rate_to

    await message.answer(
        f"💱 **Результат конвертації (за курсом НБУ):**\n"
        f"{amount:,.2f} {from_curr} = **{result:,.2f} {to_curr}**",
        parse_mode="Markdown"
    )