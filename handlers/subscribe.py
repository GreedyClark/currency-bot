from aiogram import Router, types
from aiogram.filters import Command
from database.db import add_subscription, remove_subscriptions_by_user

router = Router()


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message) -> None:
    """
    Обробник команди /subscribe [валюта] [умова: >, <, >=, <=] [цільовий_курс]
    Приклад: /subscribe usd > 41.5
    """
    if not message.text:
        return

    args = message.text.split()[1:]
    if len(args) < 3:
        await message.answer(
            "❌ <b>Некоректний формат команди.</b>\n\n"
            "Використовуйте: <code>/subscribe [usd/eur] [>, <, >=, <=] [курс]</code>\n"
            "Приклад: <code>/subscribe usd > 41.5</code>"
        )
        return

    currency = args[0].upper()
    condition = args[1]
    raw_rate = args[2].replace(",", ".")

    if currency not in ["USD", "EUR"]:
        await message.answer("❌ Підписка доступна тільки для <b>USD</b> та <b>EUR</b>.")
        return

    if condition not in [">", "<", ">=", "<="]:
        await message.answer("❌ Некоректна умова. Допустимі варіанти: <code>></code>, <code><</code>, <code>>=</code>, <code><=</code>.")
        return

    try:
        target_rate = float(raw_rate)
        if target_rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, вкажіть додатне число для цільового курсу.")
        return

    success = await add_subscription(
        user_id=message.from_user.id,
        currency=currency,
        condition=condition,
        target_rate=target_rate
    )

    if success:
        await message.answer(
            f"✅ <b>Підписку успішно створено!</b>\n"
            f"Ми сповістимо вас, коли курс <b>{currency}</b> стане <b>{condition} <code>{target_rate:.2f}</code> UAH</b>."
        )
    else:
        await message.answer(f"ℹ️ У вас вже існує точно така ж підписка на <b>{currency} {condition} <code>{target_rate:.2f}</code> UAH</b>.")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message) -> None:
    """Скасовує всі підписки користувача."""
    deleted_count = await remove_subscriptions_by_user(message.from_user.id)
    if deleted_count > 0:
        await message.answer(f"✅ Успішно скасовано всі ваші підписки (видалено: <b>{deleted_count}</b>).")
    else:
        await message.answer("ℹ️ У вас немає активних підписок.")