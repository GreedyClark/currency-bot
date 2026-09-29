import logging
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database.db import get_rate_history
from services.nbu_api import get_nbu_rates

logger = logging.getLogger(__name__)
app = FastAPI(title="Currency Bot Mini App API")

# Підключаємо статичні файли для Mini App
app.mount("/static", StaticFiles(directory="webapp"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("webapp/index.html")


@app.get("/api/rates")
async def get_rates():
    """Повертає розширений список курсів валют НБУ (включаючи UAH = 1.0)."""
    rates_data = await get_nbu_rates()
    res = {"UAH": 1.0}  # Базова валюта
    target_currencies = ["USD", "EUR", "PLN", "GBP", "CHF"]

    if rates_data:
        for r in rates_data:
            code = r.get("cc")
            if code in target_currencies:
                res[code] = r.get("rate")
    return res


@app.get("/api/history")
async def get_history_api(
    currency: str = Query("USD", description="Код валюти (USD/EUR/PLN/GBP/CHF)"),
    days: int = Query(30, ge=1, le=90, description="Кількість днів")
):
    history = await get_rate_history(currency=currency, days=days, source="nbu")
    history = list(reversed(history))
    return {
        "currency": currency.upper(),
        "data": [
            {
                "date": item["date"],
                "rate": item["rate_buy"]
            }
            for item in history
        ]
    }