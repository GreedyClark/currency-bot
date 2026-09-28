import logging
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)

NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"


async def get_nbu_rates() -> list:
    """Отримує поточні курси валют від НБУ."""
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(NBU_API_URL) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Помилка API НБУ: статус {response.status}")
                    return []
    except Exception as e:
        logger.error(f"Помилка підключення до API НБУ: {e}")
        return []


async def get_nbu_rate_by_code(currency_code: str) -> float | None:
    """Повертає курс конкретної валюти за її кодом (наприклад, USD)."""
    rates = await get_nbu_rates()
    for rate in rates:
        if rate.get("cc") == currency_code.upper():
            return rate.get("rate")
    return None


async def get_nbu_history_range(days: int = 30) -> list:
    """
    Завантажує історію курсів USD та EUR з API НБУ за останні N днів.
    Використовується для первинного заповнення БД (backfill).
    """
    results = []
    today = datetime.now()
    timeout = aiohttp.ClientTimeout(total=10)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for i in range(days):
                date_target = today - timedelta(days=i)
                date_str = date_target.strftime("%Y%m%d")
                url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&date={date_str}&json"

                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            results.append(data[0])

                url_eur = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=EUR&date={date_str}&json"
                async with session.get(url_eur) as resp_eur:
                    if resp_eur.status == 200:
                        data_eur = await resp_eur.json()
                        if data_eur:
                            results.append(data_eur[0])
    except Exception as e:
        logger.error(f"Помилка під час завантаження історії з API НБУ: {e}")

    return results