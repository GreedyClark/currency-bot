import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"
TARGET_CURRENCIES = {"USD", "EUR", "PLN", "GBP", "CHF"}


async def get_nbu_rates(date_str: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict]:
    """
    Отримує курс валют від НБУ.
    Якщо вказано date_str у форматі YYYYMMDD, повертає курс на ту дату.
    Можна передати існуючу aiohttp.ClientSession для повторного використання.
    """
    url = NBU_API_URL
    if date_str:
        url += f"&date={date_str}"

    should_close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        should_close_session = True

    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                return data if isinstance(data, list) else []
            logger.error(f"Помилка NBU API (дата {date_str}): статус {response.status}")
            return []
    except Exception as e:
        logger.error(f"Помилка при з'єднанні з NBU API (дата {date_str}): {e}")
        return []
    finally:
        if should_close_session and not session.closed:
            await session.close()


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


async def get_nbu_history_range(days: int = 30) -> List[Dict]:
    """
    Отримує курси НБУ за останні N днів (запит на кожну дату паралельно).
    """
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]

    semaphore = asyncio.Semaphore(5)

    async def fetch_for_date(date_str: str, session: aiohttp.ClientSession) -> List[Dict]:
        async with semaphore:
            return await get_nbu_rates(date_str, session=session)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_for_date(d, session) for d in dates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_records: List[Dict] = []
    seen_keys = set()

    for date_str, res in zip(dates, results):
        if isinstance(res, Exception):
            logger.error(f"Не вдалося отримати курси НБУ за дату {date_str}: {res}")
            continue

        if not isinstance(res, list):
            continue

        for item in res:
            cc = item.get("cc")
            exchangedate = item.get("exchangedate")
            if cc in TARGET_CURRENCIES and exchangedate:
                dedup_key = (exchangedate, cc)
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    all_records.append(item)

    return all_records