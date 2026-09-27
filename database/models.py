"""
SQL-скрипти для ініціалізації таблиць бази даних.
"""

# Таблиця підписок користувачів на сповіщення про зміну курсу
CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    currency TEXT NOT NULL,
    condition TEXT NOT NULL,  -- Знаки: '>', '<', '>=', '<='
    target_rate REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, currency, condition, target_rate)
);
"""

# Таблиця для збереження щоденної історії курсів (для побудови графіків)
CREATE_RATE_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS rate_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,        -- Формат: YYYY-MM-DD
    currency TEXT NOT NULL,    -- USD, EUR тощо
    source TEXT NOT NULL,      -- 'nbu' або 'mono'
    rate_buy REAL NOT NULL,    -- Курс купівлі (або офіційний для НБУ)
    rate_sell REAL,            -- Курс продажу (опційно для НБУ)
    UNIQUE(date, currency, source)
);
"""