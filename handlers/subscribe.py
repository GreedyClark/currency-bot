from aiogram import Router, types
from aiogram.filters import Command
from database.db import add_subscription, get_user_subscriptions, delete_subscription

router = Router()

ALLOWED_SUB_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    """
    Формат: /subscribe <валюта> <умова> <курс>
    Приклад: /subscribe usd > 41.5
    """
    args = message.text.split()[1:]
    if len(args) < 3:
        await message.answer(
            "⚠️ <b>Формат команди:</b>\n"
            "<code>/subscribe <валюта> <умова> <курс></code>\n\n"
            "<b>Приклади:</b>\n"
            "• <code>/subscribe usd > 41.5</code>\n"
            "• <code>/subscribe eur < 44.0</code>\n"
            "• <code>/subscribe pln > 10.2</code>\n\n"
            "Доступні валюти: USD, EUR, PLN, GBP, CHF."
        )
        return

    curr = args[0].upper()
    cond = args[1]

    try:
        target_rate = float(args[2].replace(",", "."))
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне число для курсу.")
        return

    if curr not in ALLOWED_SUB_CURRENCIES:
        await message.answer("❌ Підписка можлива лише на валюти: USD, EUR, PLN, GBP, CHF.")
        return

    if cond not in [">", "<"]:
        await message.answer("❌ Умова має бути <code>></code> (більше) або <code><</code> (менше).")
        return

    if target_rate <= 0:
        await message.answer("❌ Курс має бути більшим за 0.")
        return

    success = await add_subscription(
        user_id=message.from_user.id,
        currency=curr,
        condition=cond,
        target_rate=target_rate
    )

    if success:
        await message.answer(
            f"✅ <b>Підписку успішно збережено!</b>\n\n"
            f"Ми сповістимо вас, коли курс <b>{curr}</b> буде <b>{cond} <code>{target_rate:.2f}</code> UAH</b>."
        )
    else:
        await message.answer(
            f"⚠️ У вас вже існує точно така ж підписка на <b>{curr} {cond} <code>{target_rate:.2f}</code> UAH</b>."
        )


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message):
    """Показує список активних підписок користувача з можливістю видалення."""
    subs = await get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("ℹ️ У вас немає активних підписок.")
        return

    args = message.text.split()[1:]
    if args:
        try:
            sub_id = int(args[0])
            deleted = await delete_subscription(sub_id, message.from_user.id)
            if deleted:
                await message.answer(f"✅ Підписку #<code>{sub_id}</code> скасовано.")
            else:
                await message.answer(f"❌ Підписку #<code>{sub_id}</code> не знайдено.")
            return
        except ValueError:
            pass

    text_lines = ["<b>📋 Ваші активні підписки:</b>\n"]
    for s in subs:
        text_lines.append(
            f"• ID <code>{s['id']}</code>: <b>{s['currency']}</b> {s['condition']} <code>{s['target_rate']:.2f}</code> UAH"
        )
    text_lines.append("\nЩоб скасувати підписку, введіть:\n<code>/unsubscribe <ID></code>")

    await message.answer("\n".join(text_lines))