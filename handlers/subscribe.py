from aiogram import Router, types
from aiogram.filters import Command
from database.db import add_subscription, remove_subscriptions_by_user

router = Router()

VALID_CONDITIONS = [">", "<", ">=", "<="]
VALID_CURRENCIES = ["USD", "EUR"]


@router.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message) -> None:
    """
    Обробник команди /subscribe [валюта] [умова] [значення].
    Приклад: /subscribe usd > 41.5
    """
    if not message.text or not message.from_user:
        return

    args = message.text.split()[1:]

    # Перевірка кількості аргументів
    if len(args) != 3:
        await message.answer(
            "❌ **Некоректний формат!**\n\n"
            "Використовуйте: `/subscribe [валюта] [умова] [значення]`\n"
            "Доступні умови: `>`, `<`, `>=`, `<=`\n"
            "Приклад: `/subscribe usd > 41.5`",
            parse_mode="Markdown"
        )
        return

    currency, condition, target_rate_str = args[0].upper(), args[1], args[2]

    # Валідація валюти
    if currency not in VALID_CURRENCIES:
        await message.answer("❌ Підтримуються тільки валюти **USD** та **EUR**.", parse_mode="Markdown")
        return

    # Валідація умови
    if condition not in VALID_CONDITIONS:
        await message.answer(f"❌ Некоректна умова. Дозволені значення: {', '.join(VALID_CONDITIONS)}")
        return

    # Валідація цільового курсу
    try:
        target_rate = float(target_rate_str)
        if target_rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Значення курсу має бути додатним числом!")
        return

    # Збереження підписки в БД
    success = await add_subscription(
        user_id=message.from_user.id,
        currency=currency,
        condition=condition,
        target_rate=target_rate
    )

    if success:
        await message.answer(
            f"✅ **Підписку успішно створено!**\n\n"
            f"Я надішлю сповіщення, коли курс **{currency}** відповідатиме умові: "
            f"`{condition} {target_rate}`",
            parse_mode="Markdown"
        )
    else:
        await message.answer("⚠️ Така підписка у вас вже існує!")


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message) -> None:
    """
    Обробник команди /unsubscribe.
    Видаляє всі активні підписки користувача.
    """
    if not message.from_user:
        return

    count = await remove_subscriptions_by_user(message.from_user.id)
    if count > 0:
        await message.answer(f"🗑 Успішно скасовано всі ваші підписки (видалено: {count}).")
    else:
        await message.answer("ℹ️ У вас не було активних підписок.")