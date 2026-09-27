import aiohttp
from typing import Optional, List, Dict, Any


MONO_API_URL = "https://api.monobank.ua/bank/currency"

# Коди ISO 4217
CURRENCY_CODES = {
    840: "USD",
    978: "EUR",
    980: "UAH"
}


async def get_mono_rates() -> List[Dict[str, Any]]:
    """
    Отримує курси валют від Monobank.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(MONO_API_URL, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                return []
    except (aiohttp.ClientError, TimeoutError):
        return []


async def get_mono_rate_by_code(code: str) -> Optional[Dict[str, float]]:
    """
    Повертає словник із курсами купівлі та продажу для USD або EUR від Monobank.
    Приклад відповіді: {'buy': 41.20, 'sell': 41.70}
    """
    rates = await get_mono_rates()
    target_code = code.upper()

    # Шукаємо код валюти за її ISO номером (наприклад, USD = 840)
    currency_code = None
    for numeric_code, str_code in CURRENCY_CODES.items():
        if str_code == target_code:
            currency_code = numeric_code
            break

    if not currency_code:
        return None

    for rate in rates:
        # 980 — це UAH
        if rate.get("currencyCodeA") == currency_code and rate.get("currencyCodeB") == 980:
            return {
                "buy": float(rate.get("rateBuy", 0)),
                "sell": float(rate.get("rateSell", 0) or rate.get("rateCross", 0))
            }
    return None