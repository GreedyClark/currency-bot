from aiogram import Router, types
from aiogram.filters import Command

router = Router()


def get_help_text() -> str:
    """Формує текст довідки зі списком усіх команд бота."""
    return (
        "<b>📖 Довідка по командах</b>\n\n"
        "<b>/start</b> або <b>/menu</b>\n"
        "Показати головне меню з кнопками.\n\n"
        "<b>/rate</b>\n"
        "Поточний курс усіх валют (USD, EUR, PLN, GBP, CHF) до гривні.\n\n"
        "<b>/convert</b> <i>сума валюта</i> або <i>сума з_валюти у_валюту</i>\n"
        "Конвертація суми. Приклади:\n"
        "• <code>/convert 100 usd</code> — 100 USD у гривні\n"
        "• <code>/convert 100 usd eur</code> — 100 USD у євро\n\n"
        "<b>/subscribe</b> <i>валюта умова значення</i>\n"
        "Підписка на сповіщення про курс. Приклад:\n"
        "• <code>/subscribe usd &gt; 41.5</code>\n\n"
        "<b>/mysubs</b>\n"
        "Список ваших активних підписок.\n\n"
        "<b>/unsubscribe</b>\n"
        "Скасувати підписку (покаже кнопки для вибору).\n\n"
        "<b>/history</b> <i>валюта дні</i>\n"
        "Графік історії курсу. Приклад:\n"
        "• <code>/history pln 14</code>\n\n"
        "<b>/help</b>\n"
        "Показати цю довідку."
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обробник команди /help."""
    await message.answer(get_help_text())