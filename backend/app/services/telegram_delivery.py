from __future__ import annotations

import json
import re
from collections.abc import Iterator
from html import escape, unescape
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.database import MovieDatabase


class TelegramConfigurationError(RuntimeError):
    pass


class TelegramDeliveryError(RuntimeError):
    pass


class TelegramPhotoRejectedError(TelegramDeliveryError):
    pass


MESSAGE_LIMIT = 4096
CAPTION_LIMIT = 1024
MAX_ALBUM_FILMS = 5


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _telegram_length(html: str) -> int:
    visible_text = unescape(re.sub(r"<[^>]+>", "", html))
    return len(visible_text.encode("utf-16-le")) // 2


def _format_movie(movie: dict[str, Any], file_name: str, number: int | None) -> str:
    title = _shorten(movie["title"], 300)
    original_title = movie["original_title"]
    year = movie["release_year"]
    heading = f"{number}. {title}" if number is not None else title
    if year:
        heading += f" ({year})"
    lines = [f"<b>{escape(heading)}</b>"]
    if original_title and original_title != movie["title"]:
        lines.append(escape(_shorten(original_title, 300)))

    genres = " · ".join(genre["display_name"] for genre in movie["genres"])
    if genres:
        lines.append(escape(_shorten(genres, 220)))
    if number is None:
        directors = ", ".join(
            credit["display_name"] for credit in movie["credits"]
            if credit["credit_type"] == "director"
        )
        lines.append("Тип: фильм")
        if countries := movie.get("countries"):
            lines.append("Страны: " + escape(_shorten(", ".join(countries), 220)))
        if directors:
            lines.append("Режиссёр: " + escape(_shorten(directors, 220)))
        if runtime := movie["runtime_minutes"]:
            lines.append(f"Длительность: {runtime} мин")

    ratings = [
        f"{source}: {rating:.1f}"
        for source, rating in (("IMDb", movie["imdb_rating"]), ("TMDB", movie["tmdb_rating"]))
        if rating and 0 < rating <= 10
    ]
    if ratings:
        lines.append(" · ".join(ratings))
    if number is None and (overview := " ".join(movie["overview"].split())):
        sentences = re.split(r"(?<=[.!?…])\s+", overview, maxsplit=4)
        lines.extend(("", escape(_shorten(" ".join(sentences[:4]), 500))))

    lines.extend(("", f"Имя файла: <code>{escape(file_name)}</code>"))
    links = []
    if tmdb_id := movie["tmdb_id"]:
        links.append(f'<a href="https://www.themoviedb.org/movie/{tmdb_id}">TMDB</a>')
    if (imdb_id := movie["imdb_id"]) and re.fullmatch(r"tt[0-9]+", imdb_id):
        links.append(f'<a href="https://www.imdb.com/title/{imdb_id}/">IMDb</a>')
    if links:
        lines.append(" · ".join(links))
    return "\n".join(lines)


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
        if len(text) > MESSAGE_LIMIT:
            raise TelegramDeliveryError("Сообщение Telegram длиннее 4096 символов")
        data = self._call(token, "sendMessage", {"chat_id": chat_id, "text": text})
        if not data.get("ok"):
            description = data.get("description", "Telegram отклонил сообщение")
            raise TelegramDeliveryError(str(description))
        return int(data["result"]["message_id"])

    def send_movie_requests(
        self, movies: list[tuple[dict[str, Any], str]], *, prefer_posters: bool = False
    ) -> Iterator[tuple[int, int]]:
        if not movies:
            raise TelegramDeliveryError("Список фильмов для отправки пуст")
        token, chat_id = self._credentials()
        if len(movies) == 1:
            movie, file_name = movies[0]
            text = "<b>Запрос на загрузку</b>\n\n" + _format_movie(movie, file_name, None)
            poster_url = movie["poster_url"]
            if poster_url:
                if _telegram_length(text) <= CAPTION_LIMIT:
                    if (message_id := self._try_photo(token, chat_id, poster_url, text)) is not None:
                        yield 0, message_id
                        return
                else:
                    if prefer_posters:
                        caption = "<b>Запрос на загрузку</b>\n\n" + _format_movie(movie, file_name, 1)
                        if _telegram_length(caption) > CAPTION_LIMIT:
                            caption = f"Запрос на загрузку\n<code>{escape(file_name)}</code>"
                        if (message_id := self._try_photo(token, chat_id, poster_url, caption)) is not None:
                            yield 0, message_id
                            self._send_request_text(token, chat_id, text)
                            return
                    text += f'\n<a href="{escape(poster_url)}">Постер</a>'
            yield 0, self._send_request_text(token, chat_id, text)
            return

        heading = f"<b>Запрос на загрузку · {len(movies)} фильмов</b>"
        blocks = [_format_movie(movie, file_name, index)
                  for index, (movie, file_name) in enumerate(movies, 1)]
        photos = []
        if len(movies) <= MAX_ALBUM_FILMS:
            for index, ((movie, _), block) in enumerate(zip(movies, blocks, strict=True)):
                caption = f"{heading}\n\n{block}"
                if prefer_posters and _telegram_length(caption) > CAPTION_LIMIT:
                    caption = f"{heading}\n\n{index + 1}. <code>{escape(movies[index][1])}</code>"
                if (poster := movie["poster_url"]) and _telegram_length(caption) <= CAPTION_LIMIT:
                    photos.append((index, poster, caption))

        photo_indices = set()
        album_ids = self._try_album(token, chat_id, photos) if len(photos) >= 2 else None
        if album_ids:
            for (index, _, _), message_id in zip(photos, album_ids, strict=True):
                photo_indices.add(index)
                yield index, message_id
        else:
            for index, poster, caption in photos:
                if (message_id := self._try_photo(token, chat_id, poster, caption)) is not None:
                    photo_indices.add(index)
                    yield index, message_id

        text = heading
        text_indices = []
        for index, formatted_movie in enumerate(blocks):
            if index in photo_indices and not album_ids:
                continue
            block = "\n\n" + formatted_movie
            if _telegram_length(text + block) > MESSAGE_LIMIT:
                message_id = self._send_request_text(token, chat_id, text)
                for sent_index in text_indices:
                    if sent_index not in photo_indices:
                        yield sent_index, message_id
                text = heading
                text_indices = []
            text += block
            text_indices.append(index)
        if text_indices:
            message_id = self._send_request_text(token, chat_id, text)
            for index in text_indices:
                if index not in photo_indices:
                    yield index, message_id

    def _try_photo(self, token: str, chat_id: str, poster: str, caption: str) -> int | None:
        try:
            data = self._call(token, "sendPhoto", {
                "chat_id": chat_id, "photo": poster, "caption": caption,
                "parse_mode": "HTML",
            })
        except TelegramPhotoRejectedError:
            return None
        return int(data["result"]["message_id"]) if data.get("ok") else None

    def _try_album(
        self, token: str, chat_id: str, photos: list[tuple[int, str, str]]
    ) -> list[int] | None:
        media = [
            {"type": "photo", "media": poster, "caption": caption, "parse_mode": "HTML"}
            for _, poster, caption in photos
        ]
        try:
            data = self._call(token, "sendMediaGroup", {
                "chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False),
            })
        except TelegramPhotoRejectedError:
            return None
        if not data.get("ok"):
            return None
        messages = data.get("result")
        if not isinstance(messages, list) or len(messages) != len(photos):
            raise TelegramDeliveryError("Telegram вернул неожиданный ответ для альбома")
        return [int(message["message_id"]) for message in messages]

    def _send_request_text(self, token: str, chat_id: str, text: str) -> int:
        data = self._call(token, "sendMessage", {
            "chat_id": chat_id, "text": text, "parse_mode": "HTML",
            "link_preview_options": '{"is_disabled":true}',
        })
        if not data.get("ok"):
            raise TelegramDeliveryError(str(data.get("description", "Telegram отклонил сообщение")))
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

    def find_private_chats(self, bot_token: str | None = None) -> list[dict[str, str]]:
        token = (bot_token or "").strip() or self._credentials()[0]
        me = self._call(token, "getMe")
        if not me.get("ok"):
            raise TelegramConfigurationError("Неверный токен Telegram-бота")
        updates = self._call(token, "getUpdates", {"limit": "100", "timeout": "0"})
        if not updates.get("ok"):
            raise TelegramDeliveryError(
                str(updates.get("description", "Не удалось получить чаты Telegram"))
            )
        chats: dict[str, str] = {}
        for update in updates.get("result", []):
            message = update.get("message") or update.get("edited_message") or {}
            chat = message.get("chat") or {}
            if chat.get("type") != "private" or chat.get("id") is None:
                continue
            label = chat.get("first_name") or chat.get("username") or "Личный чат"
            chats[str(chat["id"])] = str(label)
        return [
            {"chat_id": chat_id, "label": label}
            for chat_id, label in sorted(chats.items(), key=lambda item: item[1].casefold())
        ]

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
            if (method in {"sendPhoto", "sendMediaGroup"}
                    and isinstance(error, HTTPError) and error.code == 400):
                raise TelegramPhotoRejectedError("Telegram отклонил постер") from error
            raise TelegramDeliveryError(
                "Не удалось отправить сообщение в Telegram"
            ) from error
