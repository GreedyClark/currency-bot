CREATE_RATES_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS rates_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    rate_buy REAL NOT NULL,
    rate_sell REAL,
    date TEXT NOT NULL
);
"""

CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    currency TEXT NOT NULL,
    condition TEXT NOT NULL,
    target_rate REAL NOT NULL
);
"""