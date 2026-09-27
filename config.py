from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Клас налаштувань застосунку.
    Значення автоматично зчитуються з файлу .env або змінних середовища.
    """
    BOT_TOKEN: str
    DB_PATH: str = "database/currency.db"

    # Конфігурація для зчитування з .env файлу
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Глобальний екземпляр налаштувань
settings = Settings()