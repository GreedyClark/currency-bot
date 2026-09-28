import io
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile

from services.nbu_api import get_nbu_rates, get_nbu_rate_by_code
from database.db import add_subscription, get_rate_history
from handlers.history import generate_chart
from handlers.start import get_main_menu_keyboard

router = Router()


# --- FSM Стани ---
class ConvertState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_amount = State()


class SubscribeState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_condition = State()
    waiting_for_rate = State()


class HistoryState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_days = State()


# --- Допоміжні клавіатури ---
def get_back_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    return builder.as_markup()


def get_currency_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="USD 💵", callback_data="select_curr_USD")
    builder.button(text="EUR 💶", callback_data="select_curr_EUR")
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(2, 1)
    return builder.as_markup()


# --- Кнопка "Назад" ---
@router.callback_query(F.data == "menu_back")
async def process_back(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "<b>Вітаю у Currency Bot!</b> 👋\n\nОберіть потрібний розділ за допомогою кнопок нижче:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# --- 1. Курс валют (menu_rate) ---
@router.callback_query(F.data == "menu_rate")
async def process_menu_rate(callback: types.CallbackQuery) -> None:
    rates = await get_nbu_rates()
    if not rates:
        await callback.message.edit_text("❌ Не вдалося отримати курси валют.", reply_markup=get_back_keyboard())
        await callback.answer()
        return

    text_lines = ["<b>📊 Поточний курс валют (НБУ):</b>\n"]
    for r in rates:
        code = r.get("cc")
        if code in ["USD", "EUR"]:
            val = r.get("rate")
            text_lines.append(f"<b>{code}:</b> <code>{val:.2f}</code> UAH")

    text_lines.append("\nОновлено автоматично.")
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Оновити", callback_data="menu_rate")
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(1)

    await callback.message.edit_text("\n".join(text_lines), reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


# --- 2. Конвертер (menu_convert) ---
@router.callback_query(F.data == "menu_convert")
async def process_menu_convert(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ConvertState.waiting_for_currency)
    await callback.message.edit_text("🔄 <b>Конвертер</b>\n\nОберіть валюту:", reply_markup=get_currency_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(ConvertState.waiting_for_currency, F.data.startswith("select_curr_"))
async def process_convert_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    curr = callback.data.split("_")[-1]
    await state.update_data(currency=curr)
    await state.set_state(ConvertState.waiting_for_amount)
    await callback.message.edit_text(
        f"Введіть суму у <b>{curr}</b> для конвертації в UAH:",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(ConvertState.waiting_for_amount)
async def process_convert_amount(message: types.Message, state: FSMContext) -> None:
    text = message.text.replace(",", ".") if message.text else ""
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне додатне число:", reply_markup=get_back_keyboard())
        return

    data = await state.get_data()
    curr = data.get("currency", "USD")
    rate = await get_nbu_rate_by_code(curr)

    if not rate:
        await message.answer("❌ Не вдалося отримати актуальний курс.", reply_markup=get_back_keyboard())
        await state.clear()
        return

    result = amount * rate
    await state.clear()

    res_text = (
        f"💱 <b>Результат конвертації:</b>\n\n"
        f"<code>{amount:,.2f}</code> {curr} = <code>{result:,.2f}</code> UAH\n"
        f"<i>(Курс НБУ: {rate:.2f} UAH)</i>"
    )
    await message.answer(res_text, reply_markup=get_main_menu_keyboard(), parse_mode="HTML")


# --- 3. Підписки (menu_subscribe) ---
@router.callback_query(F.data == "menu_subscribe")
async def process_menu_subscribe(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SubscribeState.waiting_for_currency)
    await callback.message.edit_text("🔔 <b>Підписка на курс</b>\n\nОберіть валюту:", reply_markup=get_currency_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(SubscribeState.waiting_for_currency, F.data.startswith("select_curr_"))
async def process_sub_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    curr = callback.data.split("_")[-1]
    await state.update_data(currency=curr)
    await state.set_state(SubscribeState.waiting_for_condition)

    builder = InlineKeyboardBuilder()
    builder.button(text="Більше ніж (>)", callback_data="sub_cond_>")
    builder.button(text="Менше ніж (<)", callback_data="sub_cond_<")
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(2, 1)

    await callback.message.edit_text(f"Оберіть умову для <b>{curr}</b>:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(SubscribeState.waiting_for_condition, F.data.startswith("sub_cond_"))
async def process_sub_condition(callback: types.CallbackQuery, state: FSMContext) -> None:
    cond = callback.data.split("_")[-1]
    await state.update_data(condition=cond)
    await state.set_state(SubscribeState.waiting_for_rate)

    await callback.message.edit_text(
        f"Введіть цільове значення курсу UAH (наприклад: <code>41.5</code>):",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SubscribeState.waiting_for_rate)
async def process_sub_rate(message: types.Message, state: FSMContext) -> None:
    text = message.text.replace(",", ".") if message.text else ""
    try:
        target_rate = float(text)
        if target_rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне додатне число:", reply_markup=get_back_keyboard())
        return

    data = await state.get_data()
    curr = data.get("currency", "USD")
    cond = data.get("condition", ">")

    await add_subscription(
        user_id=message.from_user.id,
        currency=curr,
        condition=cond,
        target_rate=target_rate
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Підписку успішно збережено!</b>\n\n"
        f"Ми сповістимо вас, коли курс <b>{curr}</b> буде <b>{cond} {target_rate:.2f} UAH</b>.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )


# --- 4. Історія (menu_history) ---
@router.callback_query(F.data == "menu_history")
async def process_menu_history(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.set_state(HistoryState.waiting_for_currency)
    await callback.message.edit_text("📊 <b>Історія курсу</b>\n\nОберіть валюту:", reply_markup=get_currency_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(HistoryState.waiting_for_currency, F.data.startswith("select_curr_"))
async def process_history_currency(callback: types.CallbackQuery, state: FSMContext) -> None:
    curr = callback.data.split("_")[-1]
    await state.update_data(currency=curr)
    await state.set_state(HistoryState.waiting_for_days)

    builder = InlineKeyboardBuilder()
    builder.button(text="7 днів", callback_data="hist_days_7")
    builder.button(text="14 днів", callback_data="hist_days_14")
    builder.button(text="30 днів", callback_data="hist_days_30")
    builder.button(text="⬅️ Назад", callback_data="menu_back")
    builder.adjust(3, 1)

    await callback.message.edit_text(f"Оберіть період для <b>{curr}</b>:", reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(HistoryState.waiting_for_days, F.data.startswith("hist_days_"))
async def process_history_days(callback: types.CallbackQuery, state: FSMContext) -> None:
    days = int(callback.data.split("_")[-1])
    data = await state.get_data()
    curr = data.get("currency", "USD")
    await state.clear()

    await callback.message.edit_text("📊 Генерую графік...")

    history_data = await get_rate_history(currency=curr, days=days, source="nbu")
    if not history_data or len(history_data) < 2:
        await callback.message.edit_text(
            f"ℹ️ Для побудови графіка недостатньо даних в БД за останні {days} днів.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return

    history_data = list(reversed(history_data))
    chart_buf = generate_chart(history_data, curr)
    photo = BufferedInputFile(chart_buf.getvalue(), filename=f"{curr}_history.png")

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photo,
        caption=f"📈 Динаміка курсу <b>{curr}</b> за останні {len(history_data)} дн.",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()