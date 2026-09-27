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
│   ├── init.py
│   ├── models.py             # DDL-запити для створення таблиць
│   └── db.py                 # Асинхронні CRUD-операції з SQLite
├── services/
│   ├── init.py
│   ├── nbu_api.py            # Сервіс запитів до API НБУ
│   ├── mono_api.py           # Сервіс запитів до API Monobank
│   └── scheduler.py          # Автоматичні задачи (підписки, збереження історії)
├── handlers/
│   ├── init.py
│   ├── start.py             # Команди /start, /help
│   ├── rate.py               # Команди /rate, /convert
│   ├── subscribe.py          # Команди /subscribe, /unsubscribe
│   └── history.py            # Команда /history та Inline-режим
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

/convert — Конвертація суми між USD, EUR та UAH (приклад: /convert 100 usd uah)

/subscribe — Підписка на сповіщення при досягненні курсу (приклад: /subscribe usd > 41.5)

/unsubscribe — Видалення всіх активних підписок

/history — Графік зміни курсу валюти за N днів (приклад: /history usd 7)

🔍 Inline-режим
Ви можете виконувати швидку конвертацію в будь-якому чаті Telegram без додавання бота до групи. Просто почніть вводити юзернейм бота:
@username_бота 100 usd

⚙️ Автоматизація та фонова логіка
APScheduler:

Щогодини перевіряє активні підписки користувачів і надсилає сповіщення, якщо курс досяг заданого порогу.

Щодня о 18:00 автоматично записує поточні курси НБУ у базу даних для накопичення історії та побудови графіків.

Обробка помилок:

Автоматично обробляє таймаути зовнішніх API (НБУ, Monobank).

Перевіряє некоректний ввід користувача (невідомі валюти, від'ємні суми, неправильний формат команд).