from __future__ import annotations

import calendar
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.database import MovieDatabase


class PeopleRepository:
    def __init__(self, database: MovieDatabase) -> None:
        self.database = database

    def list_movie_targets(self) -> list[dict[str, int]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id, tmdb_id FROM movies WHERE tmdb_id IS NOT NULL ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_movie_target(self, movie_id: int) -> dict[str, int] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, tmdb_id FROM movies WHERE id = ? AND tmdb_id IS NOT NULL",
                (movie_id,),
            ).fetchone()
            return dict(row) if row else None

    def find_by_tmdb_id(self, tmdb_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM people WHERE tmdb_id = ?", (tmdb_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def refresh_is_due(person: dict[str, Any], now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        next_refresh = datetime.fromisoformat(person["next_refresh_at"]).replace(
            tzinfo=timezone.utc
        )
        return current >= next_refresh

    def upsert_person(self, bundle: dict[str, Any]) -> tuple[int, bool]:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        next_refresh = self._add_months(now, 6)
        translations = bundle.get("translations") or {}
        russian = next(
            (
                item.get("data") or {}
                for item in translations.get("translations", [])
                if item.get("iso_639_1") == "ru"
            ),
            {},
        )
        external_ids = bundle.get("external_ids") or {}
        name = bundle.get("name") or "Без имени"
        display_name = russian.get("name") or name
        biography = russian.get("biography") or bundle.get("biography") or ""
        profile_path = bundle.get("profile_path")

        with self.database.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM people WHERE tmdb_id = ?", (bundle["id"],)
            ).fetchone()
            connection.execute(
                """
                INSERT INTO people (
                    tmdb_id, name, display_name, also_known_as, biography,
                    birthday, deathday, place_of_birth, gender,
                    known_for_department, profile_url, homepage, imdb_id,
                    wikidata_id, last_refreshed_at, next_refresh_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tmdb_id) DO UPDATE SET
                    name = excluded.name,
                    display_name = excluded.display_name,
                    also_known_as = excluded.also_known_as,
                    biography = excluded.biography,
                    birthday = excluded.birthday,
                    deathday = excluded.deathday,
                    place_of_birth = excluded.place_of_birth,
                    gender = excluded.gender,
                    known_for_department = excluded.known_for_department,
                    profile_url = excluded.profile_url,
                    homepage = excluded.homepage,
                    imdb_id = excluded.imdb_id,
                    wikidata_id = excluded.wikidata_id,
                    last_refreshed_at = excluded.last_refreshed_at,
                    next_refresh_at = excluded.next_refresh_at,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    bundle["id"],
                    name,
                    display_name,
                    json.dumps(bundle.get("also_known_as") or [], ensure_ascii=False),
                    biography,
                    bundle.get("birthday"),
                    bundle.get("deathday"),
                    bundle.get("place_of_birth"),
                    bundle.get("gender"),
                    bundle.get("known_for_department"),
                    (
                        f"https://image.tmdb.org/t/p/h632{profile_path}"
                        if profile_path
                        else None
                    ),
                    bundle.get("homepage"),
                    external_ids.get("imdb_id") or bundle.get("imdb_id"),
                    external_ids.get("wikidata_id"),
                    now.isoformat(sep=" "),
                    next_refresh.isoformat(sep=" "),
                ),
            )
            person_id = connection.execute(
                "SELECT id FROM people WHERE tmdb_id = ?", (bundle["id"],)
            ).fetchone()["id"]
            self._replace_filmography(
                connection, person_id, bundle.get("movie_credits") or {}
            )
            return person_id, existing is None

    def link_movie_credit(
        self, movie_id: int, person_id: int, credit: dict[str, Any]
    ) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT id FROM movie_credits
                WHERE movie_id = ? AND credit_type = ?
                  AND (canonical_name = ? OR display_name = ?)
                ORDER BY id LIMIT 1
                """,
                (
                    movie_id,
                    credit["credit_type"],
                    credit["name"],
                    credit["name"],
                ),
            ).fetchone()
            values = (
                person_id,
                credit.get("credit_id"),
                credit.get("character"),
                credit.get("department"),
                credit.get("job"),
            )
            if row:
                connection.execute(
                    """
                    UPDATE movie_credits
                    SET person_id = ?, tmdb_credit_id = ?, character = ?,
                        department = ?, job = ?
                    WHERE id = ?
                    """,
                    (*values, row["id"]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO movie_credits (
                        movie_id, person_id, canonical_name, display_name,
                        credit_type, sort_order, tmdb_credit_id, character,
                        department, job
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        movie_id,
                        person_id,
                        credit["name"],
                        credit["name"],
                        credit["credit_type"],
                        credit["sort_order"],
                        credit.get("credit_id"),
                        credit.get("character"),
                        credit.get("department"),
                        credit.get("job"),
                    ),
                )
            connection.execute(
                """
                UPDATE person_filmography
                SET local_movie_id = ?
                WHERE person_id = ? AND tmdb_movie_id = (
                    SELECT tmdb_id FROM movies WHERE id = ?
                )
                """,
                (movie_id, person_id, movie_id),
            )

    def get_person(self, person_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            person = connection.execute(
                "SELECT * FROM people WHERE id = ?", (person_id,)
            ).fetchone()
            if person is None:
                return None
            credits = connection.execute(
                """
                SELECT tmdb_movie_id, local_movie_id, credit_kind, title,
                       original_title, release_year, character, department,
                       job, poster_url, vote_average
                FROM person_filmography
                WHERE person_id = ?
                ORDER BY release_year IS NULL, release_year DESC, title
                """,
                (person_id,),
            ).fetchall()
            result = dict(person)
            result["also_known_as"] = json.loads(result["also_known_as"])
            result["filmography"] = [
                {**dict(row), "in_library": row["local_movie_id"] is not None}
                for row in credits
            ]
            return result

    @staticmethod
    def _replace_filmography(
        connection: sqlite3.Connection,
        person_id: int,
        movie_credits: dict[str, Any],
    ) -> None:
        connection.execute(
            "DELETE FROM person_filmography WHERE person_id = ?", (person_id,)
        )
        for credit_kind in ("cast", "crew"):
            for item in movie_credits.get(credit_kind, []):
                tmdb_movie_id = item.get("id")
                title = item.get("title") or item.get("original_title")
                if not tmdb_movie_id or not title:
                    continue
                release_date = item.get("release_date") or ""
                release_year = (
                    int(release_date[:4]) if len(release_date) >= 4 else None
                )
                credit_key = item.get("credit_id") or ":".join(
                    str(value or "")
                    for value in (
                        credit_kind,
                        tmdb_movie_id,
                        item.get("character"),
                        item.get("department"),
                        item.get("job"),
                    )
                )
                local_movie = connection.execute(
                    "SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_movie_id,)
                ).fetchone()
                poster_path = item.get("poster_path")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO person_filmography (
                        person_id, credit_key, tmdb_movie_id, local_movie_id,
                        credit_kind, title, original_title, release_year,
                        character, department, job, poster_url, vote_average,
                        popularity
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        person_id,
                        credit_key,
                        tmdb_movie_id,
                        local_movie["id"] if local_movie else None,
                        credit_kind,
                        title,
                        item.get("original_title") or title,
                        release_year,
                        item.get("character"),
                        item.get("department"),
                        item.get("job"),
                        (
                            f"https://image.tmdb.org/t/p/w185{poster_path}"
                            if poster_path
                            else None
                        ),
                        item.get("vote_average"),
                        item.get("popularity"),
                    ),
                )

    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
