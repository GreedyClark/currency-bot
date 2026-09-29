"""
SQL-схема таблиць бази даних SQLite.
"""

CREATE_RATES_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS rates_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency TEXT NOT NULL,
    source TEXT NOT NULL,
    rate_buy REAL NOT NULL,
    rate_sell REAL NOT NULL,
    date TEXT NOT NULL,
    UNIQUE(date, currency, source)
);
"""

CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    currency TEXT NOT NULL,
    condition TEXT NOT NULL,
    target_rate REAL NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""