💱 Telegram Currency Bot
Асинхронний Telegram-бот для моніторингу курсів валют (USD, EUR) від Національного банку України та Monobank. Бот дозволяє отримувати актуальні курси, конвертувати валюти, підписуватися на сповіщення про досягнення заданого курсу, будувати графіки динаміки та використовувати зручний inline-режим у будь-якому чаті.

Проєкт виконано з дотриманням принципів чистої архітектури (Clean Architecture), розділенням відповідальності (handlers, services, database) та повною асинхронністю.

🛠 Технологічний стек
Мова програмування: Python 3.11+
Telegram Bot API: aiogram 3.x
База даних: SQLite (через асинхронну бібліотеку aiosqlite)
Планувальник задач: APScheduler 3.x
HTTP-клієнт: aiohttp
Генерація графіків: matplotlib
Валідація та конфігурація: pydantic-settings & python-dotenv

📁 Структура проєкту
currency-bot/
├── bot.py                  # Точка входу, ініціалізація бота і диспетчера
├── config.py                # Завантаження та валідація налаштувань (.env)
├── database/
│   ├── __init__.py
│   ├── models.py             # DDL-запити для створення таблиць
│   └── db.py                 # Асинхронні CRUD-операції з SQLite
├── services/
│   ├── __init__.py
│   ├── nbu_api.py            # Сервіс запитів до API НБУ
│   ├── mono_api.py           # Сервіс запитів до API Monobank
│   └── scheduler.py          # Автоматичні задачі (підписки, збереження історії)
├── handlers/
│   ├── __init__.py
│   ├── start.py             # Команди /start, /help
│   ├── rate.py               # Команди /rate, /convert
│   ├── subscribe.py          # Команди /subscribe, /unsubscribe
│   ├── history.py            # Команда /history та Inline-режим
│   └── menu_callbacks.py     # Inline-меню та FSM
├── requirements.txt          # Залежності проєкту
├── .env.example              # Шаблон файлу змінних середовища
└── README.md                 # Документація проєкту

🚀 Інструкція зі встановлення та запуску
1. Клонування репозиторію
git clone https://github.com/your-username/currency-bot.git
cd currency-bot

2. Створення та активація віртуального середовища
Windows:
python -m venv venv
venv\Scripts\activate

Linux / macOS:
python3 -m venv venv
source venv/bin/activate

3. Встановлення залежностей
pip install --upgrade pip
pip install -r requirements.txt

4. Налаштування змінних середовища
Створіть файл .env у корені проєкту (або скопіюйте з .env.example):

cp .env.example .env

Відкрийте файл .env та вкажіть ваш Telegram Bot Token, отриманий у @BotFather:

BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ
DB_PATH=database/currency.db

5. Запуск бота
python bot.py

🤖 Доступні команди та функціонал
/start — Привітання та інструкція з використання
/rate — Актуальний курс USD та EUR від НБУ та Monobank
/convert — Конвертація суми між USD, EUR та UAH
/subscribe — Підписка на сповіщення при досягненні курсу
/unsubscribe — Видалення всіх активних підписок
/history — Графік зміни курсу валюти за N днів
/menu — Показати головне меню

🔍 Inline-режим
Ви можете виконувати швидку конвертацію в будь-якому чаті Telegram без додавання бота до групи. Просто почніть вводити юзернейм бота:
@username_бота 100 usd

⚙️ Налаштування BotFather

Щоб налаштувати меню команд у Telegram для вашого бота, виконайте такі кроки:

1. Відкрийте чат із @BotFather у Telegram.
2. Надішліть команду /setcommands.
3. Оберіть вашого бота зі списку.
4. Скопіюйте та відправте наступний список команд:

start - Почати роботу з ботом
rate - Поточний курс валют
convert - Конвертувати суму
subscribe - Підписатись на сповіщення
unsubscribe - Скасувати підписки
history - Графік історії курсу
menu - Показати головне меню
