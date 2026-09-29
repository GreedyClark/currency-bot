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