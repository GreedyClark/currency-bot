import aiohttp
from typing import Optional, Dict, Any, List


NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"


async def get_nbu_rates() -> List[Dict[str, Any]]:
    """
    Отримує курси всіх валют від НБУ.
    Повертає список словників із даними або порожній список у разі помилки.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(NBU_API_URL, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                return []
    except (aiohttp.ClientError, TimeoutError):
        # Логування або обробка помилок мережі/таймауту
        return []


async def get_nbu_rate_by_code(code: str) -> Optional[float]:
    """
    Отримує офіційний курс конкретної валюти (наприклад, 'USD', 'EUR') від НБУ.
    """
    rates = await get_nbu_rates()
    for rate in rates:
        if rate.get("cc") == code.upper():
            return float(rate.get("rate", 0))
    return None