import aiohttp
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
TARGET_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}


async def get_nbu_rates(date_str: Optional[str] = None) -> List[Dict]:
    """
    Отримує курс валют від НБУ.
    Якщо вказано date_str у форматі YYYYMMDD, повертає курс на ту дату.
    """
    url = NBU_API_URL
    if date_str:
        url += f"&date={date_str}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                logger.error(f"Помилка NBU API: статус {response.status}")
                return []
    except Exception as e:
        logger.error(f"Помилка при з'єднанні з NBU API: {e}")
        return []


async def get_nbu_rate_by_code(code: str, date_str: Optional[str] = None) -> Optional[float]:
    """
    Отримує курс конкретної валюти за її кодом (USD, EUR, PLN, GBP, CHF).
    """
    rates = await get_nbu_rates(date_str)
    code_upper = code.upper()
    for item in rates:
        if item.get("cc") == code_upper:
            return float(item.get("rate", 0.0))
    return None