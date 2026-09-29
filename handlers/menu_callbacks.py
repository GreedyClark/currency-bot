import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest

from services.nbu_api import get_nbu_rates, get_nbu_rate_by_code
from database.db import add_subscription, get_rate_history
from handlers.history import generate_chart
from handlers.start import get_main_menu_keyboard
from handlers.rate import get_rate_change_indicator

logger = logging.getLogger(__name__)
router = Router()

SUPPORTED_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}
SUPPORTED_CURRENCIES_ALL = {"USD", "EUR", "PLN", "GBP", "CHF", "UAH"}


# --- FSM Стани ---
class ConvertState(StatesGroup):
    waiting_for_from_currency = State()
    waiting_for_to_currency = State()
    waiting_for_amount = State()


class SubscribeState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_condition = State()
    waiting_for_rate = State()


class HistoryState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_days = State()


# --- Допоміжні функції та клавіатури ---
async def safe_edit_or_send(
    callback: types.CallbackQuery,
    text: str,
    reply_markup: types.InlineKeyboardMarkup = None
) -> None:
    """
    Безпечно оновлює текст повідомлення або надсилає нове,
    якщо попереднє повідомлення містило фотографію (графік).
    """
    msg = callback.message
    if not msg:
        return

    if msg.photo:
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        await msg.answer(text, reply_markup=reply_markup)
        return

    try:
        await msg.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        err_msg = str(e).lower()
        if "message is not modified" in err_msg:
            await callback.answer("ℹ️ Дані вже актуальні!", show_alert=False)
            return
        elif "there is no text to edit" in err_msg or "message can't be edited" in err_msg:
            try:
                await msg.delete()
            except TelegramBadRequest:
                pass
            await msg.answer(text, reply_markup=reply_markup)
        else:
            logger.error(f"Помилка при редагуванні повідомлення: {e}")
            raise e


def get_back_keyboard() -> types.InlineKeyboardMarkup:
    """Клавіатура з кнопкою Назад."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    return builder.as_markup()


def get_currency_keyboard() -> types.InlineKeyboardMarkup:
    """Стандартна клавіатура вибору іноземної валюти (для підписок та історії)."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 USD", callback_data="select_curr_USD")
    builder.button(text="💶 EUR", callback_data="select_curr_EUR")
    builder.button(text="🇵🇱 PLN", callback_data="select_curr_PLN")
    builder.button(text="💷 GBP", callback_data="select_curr_GBP")
    builder.button(text="🇨🇭 CHF", callback_data="select_curr_CHF")
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(2, 3, 1)
    return builder.as_markup()


def get_convert_currency_keyboard(action_prefix: str, exclude_code: str = None) -> types.InlineKeyboardMarkup:
    """Клавіатура вибору валюти для конвертера (включно з UAH)."""
    builder = InlineKeyboardBuilder()
    currencies = [
        ("🇺🇦 UAH", "UAH"),
        ("💵 USD", "USD"),
        ("💶 EUR", "EUR"),
        ("🇵🇱 PLN", "PLN"),
        ("💷 GBP", "GBP"),
        ("🇨🇭 CHF", "CHF"),
    ]
    for label, code in currencies:
        if code != exclude_code:
            builder.button(text=label, callback_data=f"{action_prefix}_{code}")

    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


# --- Кнопка "Назад" ---
@router.callback_query(F.data == "menu_back")
async def process_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        await state.clear()
        text = "<b>Вітаю у Currency Bot!</b> 👋\n\nОберіть потрібний розділ за допомогою кнопок нижче:"
        await safe_edit_or_send(callback, text, reply_markup=get_main_menu_keyboard())
    finally:
        await callback.answer()


# --- 1. Курс валют (menu_rate) ---
@router.callback_query(F.data == "menu_rate")
async def process_menu_rate(callback: types.CallbackQuery) -> None:
    try:
        rates = await get_nbu_rates()
        if not rates:
            await safe_edit_or_send(callback, "❌ Не вдалося отримати курси валют.", reply_markup=get_back_keyboard())
            return

        text_lines = ["<b>📊 Поточний курс валют (НБУ):</b>\n"]
        for r in rates:
            code = r.get("cc")
            if code in SUPPORTED_CURRENCIES:
                val = r.get("rate", 0.0)
                ex_date = r.get("exchangedate", "")
                indicator = await get_rate_change_indicator(code, val, ex_date)
                text_lines.append(f"• <b>{code}</b>: <code>{val:.2f}</code> UAH{indicator}")

        text_lines.append("\nОновлено автоматично.")
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Оновити", callback_data="menu_rate")
        builder.button(text="⬅️ Назад", callback_data="menu_back")
        builder.adjust(1)

        await safe_edit_or_send(callback, "\n".join(text_lines), reply_markup=builder.as_markup())
    finally:
        await callback.answer()


# --- 2. Двосторонній Конвертер (menu_convert) ---
@router.callback_query(F.data == "menu_convert")
async def process_menu_convert(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Крок 1: Вибір валюти, З ЯКОЇ конвертуємо."""
    try:
        await state.set_state(ConvertState.waiting_for_from_currency)
        await safe_edit_or_send(
            callback,
            "🔄 <b>Мультивалютний Конвертер</b>\n\nОберіть валюту, <b>З ЯКОЇ</b> хочете конвертувати:",
            reply_markup=get_convert_currency_keyboard("convert_from")
        )
    finally:
        await callback.answer()


@router.callback_query(ConvertState.waiting_for_from_currency, F.data.startswith("convert_from_"))
async def process_convert_from_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Крок 2: Збереження From-валюти та вибір валюти, У ЯКУ конвертуємо."""
    try:
        from_curr = callback.data.split("_")[-1]
        await state.update_data(from_currency=from_curr)
        await state.set_state(ConvertState.waiting_for_to_currency)

        await safe_edit_or_send(
            callback,
            f"🔄 <b>Конвертація:</b> {from_curr} ➔ ...\n\nОберіть валюту, <b>У ЯКУ</b> хочете конвертувати:",
            reply_markup=get_convert_currency_keyboard("convert_to", exclude_code=from_curr)
        )
    finally:
        await callback.answer()


@router.callback_query(ConvertState.waiting_for_to_currency, F.data.startswith("convert_to_"))
async def process_convert_to_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Крок 3: Збереження To-валюти та запит суми."""
    try:
        to_curr = callback.data.split("_")[-1]
        await state.update_data(to_currency=to_curr)
        data = await state.get_data()
        from_curr = data.get("from_currency")

        await state.set_state(ConvertState.waiting_for_amount)
        await safe_edit_or_send(
            callback,
            f"🔄 <b>Напрямок:</b> {from_curr} ➔ {to_curr}\n\nВведіть суму у <b>{from_curr}</b>:",
            reply_markup=get_back_keyboard()
        )
    finally:
        await callback.answer()


@router.message(ConvertState.waiting_for_amount)
async def process_convert_amount(message: types.Message, state: FSMContext) -> None:
    """Крок 4: Введення суми та розрахунок крос-курсом."""
    raw_text = message.text.replace(",", ".").strip() if message.text else ""
    try:
        amount = float(raw_text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне додатне число (наприклад 100 або 50.5):", reply_markup=get_back_keyboard())
        return

    data = await state.get_data()
    from_curr = data.get("from_currency", "UAH")
    to_curr = data.get("to_currency", "USD")

    rate_from = 1.0 if from_curr == "UAH" else await get_nbu_rate_by_code(from_curr)
    rate_to = 1.0 if to_curr == "UAH" else await get_nbu_rate_by_code(to_curr)

    if not rate_from or not rate_to:
        await message.answer("❌ Не вдалося отримати актуальний курс від НБУ.", reply_markup=get_back_keyboard())
        await state.clear()
        return

    result = (amount * rate_from) / rate_to
    await state.clear()

    res_text = (
        f"💱 <b>Результат конвертації:</b>\n\n"
        f"<code>{amount:,.2f}</code> <b>{from_curr}</b> = <code>{result:,.2f}</code> <b>{to_curr}</b>\n\n"
        f"<i>• Курс {from_curr}: {rate_from:.2f} UAH\n"
        f"• Курс {to_curr}: {rate_to:.2f} UAH</i>"
    )
    await message.answer(res_text, reply_markup=get_main_menu_keyboard())


# --- Пряма команда /convert ---
@router.message(Command("convert"))
async def cmd_convert_direct(message: types.Message):
    """
    Формати прямої команди:
    • /convert <сума> <з_валюти> <у_валюту> (наприклад: /convert 100 usd eur)
    • /convert <сума> <валюта> (автоматично переводить в UAH)
    """
    args = message.text.split()[1:]
    if not args:
        await message.answer(
            "⚠️ <b>Формат команди:</b>\n"
            "<code>/convert <сума> <з_валюти> <у_валюту></code>\n\n"
            "<b>Приклади:</b>\n"
            "• <code>/convert 100 uah usd</code>\n"
            "• <code>/convert 100 usd eur</code>\n"
            "• <code>/convert 250 pln uah</code>"
        )
        return

    try:
        amount = float(args[0].replace(",", "."))
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне число для суми.")
        return

    from_curr = args[1].upper() if len(args) >= 2 else "USD"
    to_curr = args[2].upper() if len(args) >= 3 else ("UAH" if from_curr != "UAH" else "USD")

    if from_curr not in SUPPORTED_CURRENCIES_ALL or to_curr not in SUPPORTED_CURRENCIES_ALL:
        await message.answer("❌ Валюта не підтримується. Доступні: UAH, USD, EUR, PLN, GBP, CHF.")
        return

    if amount <= 0:
        await message.answer("❌ Сума має бути більшою за 0.")
        return

    rate_from = 1.0 if from_curr == "UAH" else await get_nbu_rate_by_code(from_curr)
    rate_to = 1.0 if to_curr == "UAH" else await get_nbu_rate_by_code(to_curr)

    if not rate_from or not rate_to:
        await message.answer("❌ Не вдалося отримати актуальний курс.")
        return

    result = (amount * rate_from) / rate_to

    await message.answer(
        f"💱 <b>Результат конвертації:</b>\n\n"
        f"<code>{amount:,.2f}</code> <b>{from_curr}</b> = <code>{result:,.2f}</code> <b>{to_curr}</b>\n\n"
        f"<i>• Курс {from_curr}: {rate_from:.2f} UAH\n"
        f"• Курс {to_curr}: {rate_to:.2f} UAH</i>",
        reply_markup=get_main_menu_keyboard()
    )


# --- 3. Підписки (menu_subscribe) ---
@router.callback_query(F.data == "menu_subscribe")
async def process_menu_subscribe(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(SubscribeState.waiting_for_currency)
        await safe_edit_or_send(callback, "🔔 <b>Підписка на курс</b>\n\nОберіть валюту:", reply_markup=get_currency_keyboard())
    finally:
        await callback.answer()


@router.callback_query(SubscribeState.waiting_for_currency, F.data.startswith("select_curr_"))
async def process_sub_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        curr = callback.data.split("_")[-1]
        await state.update_data(currency=curr)
        await state.set_state(SubscribeState.waiting_for_condition)

        builder = InlineKeyboardBuilder()
        builder.button(text="Більше ніж (>)", callback_data="sub_cond_>")
        builder.button(text="Менше ніж (<)", callback_data="sub_cond_<")
        builder.button(text="⬅️ Назад", callback_data="menu_back")
        builder.adjust(2, 1)

        await safe_edit_or_send(callback, f"Оберіть умову для <b>{curr}</b>:", reply_markup=builder.as_markup())
    finally:
        await callback.answer()


@router.callback_query(SubscribeState.waiting_for_condition, F.data.startswith("sub_cond_"))
async def process_sub_condition(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        cond = callback.data.split("_")[-1]
        await state.update_data(condition=cond)
        await state.set_state(SubscribeState.waiting_for_rate)

        await safe_edit_or_send(
            callback,
            "Введіть цільове значення курсу UAH (наприклад: <code>41.5</code>):",
            reply_markup=get_back_keyboard()
        )
    finally:
        await callback.answer()


@router.message(SubscribeState.waiting_for_rate)
async def process_sub_rate(message: types.Message, state: FSMContext) -> None:
    raw_text = message.text.replace(",", ".").strip() if message.text else ""
    try:
        target_rate = float(raw_text)
        if target_rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне додатне число:", reply_markup=get_back_keyboard())
        return

    data = await state.get_data()
    curr = data.get("currency", "USD")
    cond = data.get("condition", ">")

    success = await add_subscription(
        user_id=message.from_user.id,
        currency=curr,
        condition=cond,
        target_rate=target_rate
    )
    await state.clear()

    if success:
        await message.answer(
            f"✅ <b>Підписку успішно збережено!</b>\n\n"
            f"Ми сповістимо вас, коли курс <b>{curr}</b> буде <b>{cond} <code>{target_rate:.2f}</code> UAH</b>.",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            f"⚠️ У вас вже існує точно така ж підписка на <b>{curr} {cond} <code>{target_rate:.2f}</code> UAH</b>.",
            reply_markup=get_main_menu_keyboard()
        )


# --- 4. Історія (menu_history) ---
@router.callback_query(F.data == "menu_history")
async def process_menu_history(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(HistoryState.waiting_for_currency)
        await safe_edit_or_send(callback, "📊 <b>Історія курсу</b>\n\nОберіть валюту:", reply_markup=get_currency_keyboard())
    finally:
        await callback.answer()


@router.callback_query(HistoryState.waiting_for_currency, F.data.startswith("select_curr_"))
async def process_history_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        curr = callback.data.split("_")[-1]
        await state.update_data(currency=curr)
        await state.set_state(HistoryState.waiting_for_days)

        builder = InlineKeyboardBuilder()
        builder.button(text="7 днів", callback_data="hist_days_7")
        builder.button(text="14 днів", callback_data="hist_days_14")
        builder.button(text="30 днів", callback_data="hist_days_30")
        builder.button(text="⬅️ Назад", callback_data="menu_back")
        builder.adjust(3, 1)

        await safe_edit_or_send(callback, f"Оберіть період для <b>{curr}</b>:", reply_markup=builder.as_markup())
    finally:
        await callback.answer()


@router.callback_query(HistoryState.waiting_for_days, F.data.startswith("hist_days_"))
async def process_history_days(callback: types.CallbackQuery, state: FSMContext) -> None:
    try:
        days = int(callback.data.split("_")[-1])
        data = await state.get_data()
        curr = data.get("currency", "USD")
        await state.clear()

        history_data = await get_rate_history(currency=curr, days=days, source="nbu")
        if not history_data or len(history_data) < 2:
            await safe_edit_or_send(
                callback,
                f"ℹ️ Для побудови графіка недостатньо даних у базі за останні {days} днів.",
                reply_markup=get_back_keyboard()
            )
            return

        history_data = list(reversed(history_data))
        chart_buf = await generate_chart(history_data, curr)
        photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{curr}_history.png")

        if callback.message:
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass

        await callback.message.answer_photo(
            photo=photo,
            caption=f"📈 Динаміка курсу <b>{curr}</b> за останні {len(history_data)} дн.",
            reply_markup=get_main_menu_keyboard()
        )
    finally:
        await callback.answer()


# --- Фолбек для застарілих/невідомих кнопок ---
@router.callback_query()
async def process_unknown_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Фолбек для будь-яких неопрацьованих або застарілих callback-запитів."""
    await state.clear()
    await safe_edit_or_send(
        callback,
        "<b>Сесію оновлено.</b> 👋\n\nОберіть потрібний розділ за допомогою кнопок нижче:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()