from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.database import MovieDatabase


class TelegramConfigurationError(RuntimeError):
    pass


class TelegramDeliveryError(RuntimeError):
    pass


def build_movie_file_name(movie_id: int, international_title: str) -> str:
    safe_title = re.sub(r"[^\w.-]+", "_", international_title, flags=re.UNICODE)
    safe_title = safe_title.strip("._") or "movie"
    return f"CL-{movie_id:06d}_{safe_title}"[:240]


class TelegramDeliveryService:
    def __init__(self, database: MovieDatabase, timeout: int = 12) -> None:
        self.database = database
        self.timeout = timeout

    def get_settings(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT bot_token, chat_id, updated_at FROM telegram_settings WHERE id = 1"
            ).fetchone()
        if row is None:
            return {"configured": False, "chat_id": None, "updated_at": None}
        return {
            "configured": True,
            "chat_id": row["chat_id"],
            "updated_at": row["updated_at"],
        }

    def save_settings(self, bot_token: str | None, chat_id: str) -> dict[str, Any]:
        with self.database.connect() as connection:
            current = connection.execute(
                "SELECT bot_token FROM telegram_settings WHERE id = 1"
            ).fetchone()
            token = (bot_token or "").strip()
            if not token and current is not None:
                token = current["bot_token"]
            if not token:
                raise TelegramConfigurationError("Укажите токен Telegram-бота")
            connection.execute(
                """
                INSERT INTO telegram_settings (id, bot_token, chat_id)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    bot_token = excluded.bot_token,
                    chat_id = excluded.chat_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (token, chat_id.strip()),
            )
        return self.get_settings()

    def send_movie(self, international_title: str, file_name: str) -> int:
        return self.send_movies([(international_title, file_name)])

    def send_movies(self, movies: list[tuple[str, str]]) -> int:
        if not movies:
            raise TelegramDeliveryError("Список фильмов для отправки пуст")
        token, chat_id = self._credentials()
        text = "\n\n".join(
            f"{international_title}\n{file_name}"
            for international_title, file_name in movies
        )
        if len(text) > 4096:
            raise TelegramDeliveryError("Сообщение Telegram длиннее 4096 символов")
        data = self._call(token, "sendMessage", {"chat_id": chat_id, "text": text})
        if not data.get("ok"):
            description = data.get("description", "Telegram отклонил сообщение")
            raise TelegramDeliveryError(str(description))
        return int(data["result"]["message_id"])

    def send_test(self) -> int:
        token, chat_id = self._credentials()
        data = self._call(
            token,
            "sendMessage",
            {"chat_id": chat_id, "text": "CineLibrary: подключение настроено."},
        )
        if not data.get("ok"):
            raise TelegramDeliveryError(str(data.get("description", "Ошибка Telegram")))
        return int(data["result"]["message_id"])

    def _credentials(self) -> tuple[str, str]:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT bot_token, chat_id FROM telegram_settings WHERE id = 1"
            ).fetchone()
        if row is None:
            raise TelegramConfigurationError("Telegram-бот не настроен")
        return row["bot_token"], row["chat_id"]

    def _call(self, token: str, method: str, payload: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=urlencode(payload).encode("utf-8"),
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise TelegramDeliveryError(
                "Не удалось отправить сообщение в Telegram"
            ) from error
