from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from database.db import add_subscription, get_user_subscriptions, delete_subscription
from handlers.start import get_main_menu_keyboard

router = Router()

ALLOWED_SUB_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}


def format_subscriptions_list(subs: list) -> str:
    """Формує текст зі списком підписок користувача."""
    text_lines = ["<b>📋 Ваші активні підписки:</b>\n"]
    for s in subs:
        text_lines.append(
            f"• <b>{s['currency']}</b> {s['condition']} <code>{s['target_rate']:.2f}</code> UAH"
        )
    return "\n".join(text_lines)


def get_unsubscribe_keyboard(subs: list) -> types.InlineKeyboardMarkup:
    """Клавіатура з кнопкою видалення для кожної підписки."""
    builder = InlineKeyboardBuilder()
    for s in subs:
        builder.button(
            text=f"❌ {s['currency']} {s['condition']} {s['target_rate']:.2f}",
            callback_data=f"unsub_{s['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


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


@router.message(Command("mysubs"))
async def cmd_mysubs(message: types.Message):
    """Показує список активних підписок користувача (без можливості видалення)."""
    subs = await get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("ℹ️ У вас немає активних підписок.")
        return

    await message.answer(format_subscriptions_list(subs))


@router.message(Command("unsubscribe"))
async def cmd_unsubscribe(message: types.Message):
    """Показує список підписок з кнопками видалення, або видаляє за ID (сумісність зі старим форматом)."""
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

    subs = await get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("ℹ️ У вас немає активних підписок.")
        return

    await message.answer(
        "<b>🗑 Оберіть підписку для видалення:</b>",
        reply_markup=get_unsubscribe_keyboard(subs)
    )


@router.callback_query(F.data.startswith("unsub_"))
async def process_unsubscribe_callback(callback: types.CallbackQuery) -> None:
    """Видаляє підписку за натисканням inline-кнопки та оновлює список."""
    try:
        sub_id = int(callback.data.split("_")[-1])
        await delete_subscription(sub_id, callback.from_user.id)

        remaining = await get_user_subscriptions(callback.from_user.id)
        if not remaining:
            try:
                await callback.message.edit_text(
                    "✅ Усі підписки скасовано.",
                    reply_markup=get_main_menu_keyboard()
                )
            except TelegramBadRequest:
                pass
        else:
            try:
                await callback.message.edit_text(
                    "<b>🗑 Оберіть підписку для видалення:</b>",
                    reply_markup=get_unsubscribe_keyboard(remaining)
                )
            except TelegramBadRequest:
                pass
    finally:
        await callback.answer("Підписку видалено")