from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from services.nbu_api import get_nbu_rates

app = FastAPI()

# Підключаємо статичні файли WebApp
app.mount("/static", StaticFiles(directory="webapp"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("webapp/index.html")


@app.get("/api/rates")
async def get_rates():
    rates_data = await get_nbu_rates()
    res = {}
    if rates_data:
        for r in rates_data:
            code = r.get("cc")
            if code in ["USD", "EUR"]:
                res[code] = r.get("rate")
    return res