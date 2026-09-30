from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    """
    Обмежує частоту звернень одного користувача.
    Якщо користувач надсилає повідомлення/натискає кнопку частіше,
    ніж раз на `rate_limit` секунд — запит тихо ігнорується.
    """

    def __init__(self, rate_limit: float = 1.5) -> None:
        self.rate_limit = rate_limit
        self.cache: TTLCache = TTLCache(maxsize=10_000, ttl=rate_limit)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")

        if user is None:
            return await handler(event, data)

        if user.id in self.cache:
            return None

        self.cache[user.id] = True
        return await handler(event, data)