from __future__ import annotations

import os
from typing import Any

from app.database import MovieDatabase


class APICredentialsError(RuntimeError):
    pass


class APICredentialsService:
    def __init__(self, database: MovieDatabase) -> None:
        self.database = database

    def apply_saved_credentials(self) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT replicate_api_token, tmdb_read_access_token
                FROM api_credentials WHERE id = 1
                """
            ).fetchone()
        if row is None:
            return
        os.environ["REPLICATE_API_TOKEN"] = row["replicate_api_token"]
        os.environ["TMDB_READ_ACCESS_TOKEN"] = row["tmdb_read_access_token"]
        os.environ.setdefault("REPLICATE_MODEL", "google/gemini-3-flash")
        os.environ.setdefault("GEMINI_THINKING_LEVEL", "low")

    def get_settings(self) -> dict[str, Any]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT replicate_api_token, tmdb_read_access_token, updated_at
                FROM api_credentials WHERE id = 1
                """
            ).fetchone()
        return {
            "replicate_configured": bool(
                row and row["replicate_api_token"]
            ) or bool(os.getenv("REPLICATE_API_TOKEN")),
            "tmdb_configured": bool(
                row and row["tmdb_read_access_token"]
            ) or bool(os.getenv("TMDB_READ_ACCESS_TOKEN")),
            "updated_at": row["updated_at"] if row else None,
        }

    def save(self, replicate_token: str | None, tmdb_token: str | None) -> dict[str, Any]:
        with self.database.connect() as connection:
            current = connection.execute(
                """
                SELECT replicate_api_token, tmdb_read_access_token
                FROM api_credentials WHERE id = 1
                """
            ).fetchone()
            replicate = (replicate_token or "").strip()
            tmdb = (tmdb_token or "").strip()
            if not replicate and current:
                replicate = current["replicate_api_token"]
            if not tmdb and current:
                tmdb = current["tmdb_read_access_token"]
            if not replicate:
                replicate = os.getenv("REPLICATE_API_TOKEN", "").strip()
            if not tmdb:
                tmdb = os.getenv("TMDB_READ_ACCESS_TOKEN", "").strip()
            if not replicate or not tmdb:
                raise APICredentialsError("Укажите оба API-токена")
            connection.execute(
                """
                INSERT INTO api_credentials (
                    id, replicate_api_token, tmdb_read_access_token
                ) VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    replicate_api_token = excluded.replicate_api_token,
                    tmdb_read_access_token = excluded.tmdb_read_access_token,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (replicate, tmdb),
            )
        self.apply_saved_credentials()
        return self.get_settings()
