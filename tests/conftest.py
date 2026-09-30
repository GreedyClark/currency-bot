import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest_asyncio

from config import settings
from database.db import init_db


@pytest_asyncio.fixture
async def test_db(tmp_path, monkeypatch):
    """
    Тимчасова SQLite-база для кожного тесту.
    Ізольована від реальної database/currency.db, видаляється автоматично після тесту.
    """
    db_path = str(tmp_path / "test_currency.db")
    monkeypatch.setattr(settings, "DB_PATH", db_path)
    await init_db()
    yield db_path