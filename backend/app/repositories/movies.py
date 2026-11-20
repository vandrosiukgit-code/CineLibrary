from __future__ import annotations

import sqlite3
from typing import Any

from app.database import MovieDatabase
from app.schemas.movies import MovieDraftImportRequest


class MovieAlreadyExistsError(RuntimeError):
    pass


class UnknownTasteTagError(RuntimeError):
    pass


class MovieRepository:
    def __init__(self, database: MovieDatabase) -> None:
        self.database = database

    def list_movies(
        self,
        *,
        search: str | None = None,
        watched: bool | None = None,
        in_wishlist: bool | None = None,
        availability: str | None = None,
        genre: str | None = None,
        personal_rating_min: int | None = None,
        personal_rating_max: int | None = None,
        has_personal_rating: bool | None = None,
        has_taste_tags: bool | None = None,
        tag_code: str | None = None,
        sort: str = "release_desc",
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []

        if search:
            clauses.append(
                "(CASEFOLD(m.title) LIKE ? OR CASEFOLD(m.original_title) LIKE ? "
                "OR EXISTS ("
                "SELECT 1 FROM movie_credits mc WHERE mc.movie_id = m.id "
                "AND (CASEFOLD(mc.display_name) LIKE ? "
                "OR CASEFOLD(mc.canonical_name) LIKE ?)))"
            )
            pattern = f"%{search.casefold()}%"
            parameters.extend((pattern, pattern, pattern, pattern))
        if watched is not None:
            clauses.append("ud.watched = ?")
            parameters.append(int(watched))
        if in_wishlist is not None:
            clauses.append("ud.in_wishlist = ?")
            parameters.append(int(in_wishlist))
        if availability:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_files mf "
                "WHERE mf.movie_id = m.id AND mf.status = ?)"
            )
            parameters.append(availability)
        if genre:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_genres mg "
                "JOIN genres g ON g.id = mg.genre_id "
                "WHERE mg.movie_id = m.id "
                "AND (g.canonical_name = ? OR g.display_name = ?))"
            )
            parameters.extend((genre, genre))
        if personal_rating_min is not None:
            clauses.append("ud.personal_rating >= ?")
            parameters.append(personal_rating_min)
        if personal_rating_max is not None:
            clauses.append("ud.personal_rating <= ?")
            parameters.append(personal_rating_max)
        if has_personal_rating is not None:
            clauses.append(
                "ud.personal_rating IS NOT NULL"
                if has_personal_rating
                else "ud.personal_rating IS NULL"
            )
        if has_taste_tags is not None:
            tag_clause = (
                "EXISTS" if has_taste_tags else "NOT EXISTS"
            )
            clauses.append(
                f"{tag_clause} (SELECT 1 FROM movie_tags mt "
                "JOIN tags t ON t.id = mt.tag_id "
                "WHERE mt.movie_id = m.id AND t.code IS NOT NULL)"
            )
        if tag_code:
            clauses.append(
                "EXISTS (SELECT 1 FROM movie_tags mt "
                "JOIN tags t ON t.id = mt.tag_id "
                "WHERE mt.movie_id = m.id AND t.code = ?)"
            )
            parameters.append(tag_code)

        order_by = {
            "release_desc": "m.release_year DESC, m.title",
            "release_asc": "m.release_year ASC, m.title",
            "title_asc": "m.title COLLATE NOCASE ASC",
            "rating_desc": "ud.personal_rating IS NULL, ud.personal_rating DESC, m.title",
        }[sort]

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT m.id
            FROM movies m
            JOIN movie_user_data ud ON ud.movie_id = m.id
            {where}
            ORDER BY {order_by}
        """

        with self.database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [self._get_movie(connection, row["id"]) for row in rows]

    def get_movie(self, movie_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            return self._get_movie(connection, movie_id)

    def list_genres(self, *, watched: bool | None = None) -> list[str]:
        where = "WHERE ud.watched = ?" if watched is not None else ""
        parameters = (int(watched),) if watched is not None else ()
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT DISTINCT g.display_name
                FROM genres g
                JOIN movie_genres mg ON mg.genre_id = g.id
                JOIN movie_user_data ud ON ud.movie_id = mg.movie_id
                {where}
                ORDER BY g.display_name COLLATE NOCASE
                """,
                parameters,
            ).fetchall()
            return [row["display_name"] for row in rows]

    def find_by_tmdb_id(self, tmdb_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_id,)
            ).fetchone()
            return self._get_movie(connection, row["id"]) if row else None

    def list_download_requests(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, tmdb_movie_id, local_movie_id, title,
                       international_title, file_name, telegram_message_id,
                       status, requested_at
                FROM movie_download_requests
                WHERE status = 'requested'
                ORDER BY requested_at DESC, id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def create_download_request(
        self,
        *,
        tmdb_movie_id: int,
        local_movie_id: int | None,
        title: str,
        international_title: str | None = None,
        file_name: str | None = None,
        telegram_message_id: int | None = None,
    ) -> dict[str, Any]:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO movie_download_requests (
                    tmdb_movie_id, local_movie_id, title, international_title,
                    file_name, telegram_message_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, 'requested')
                ON CONFLICT(tmdb_movie_id) DO UPDATE SET
                    local_movie_id = COALESCE(
                        excluded.local_movie_id,
                        movie_download_requests.local_movie_id
                    ),
                    title = excluded.title,
                    international_title = excluded.international_title,
                    file_name = excluded.file_name,
                    telegram_message_id = excluded.telegram_message_id,
                    status = 'requested',
                    requested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    tmdb_movie_id,
                    local_movie_id,
                    title,
                    international_title,
                    file_name,
                    telegram_message_id,
                ),
            )
            row = connection.execute(
                """
                SELECT id, tmdb_movie_id, local_movie_id, title,
                       international_title, file_name, telegram_message_id,
                       status, requested_at
                FROM movie_download_requests
                WHERE tmdb_movie_id = ?
                """,
                (tmdb_movie_id,),
            ).fetchone()
            return dict(row)

    def mark_downloading(self, movie_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM movies WHERE id = ?", (movie_id,)
            ).fetchone()
            if exists is None:
                return None
            updated = connection.execute(
                """
                UPDATE movie_files
                SET status = 'downloading'
                WHERE movie_id = ? AND status != 'available'
                """,
                (movie_id,),
            ).rowcount
            if updated == 0:
                has_available = connection.execute(
                    """
                    SELECT 1 FROM movie_files
                    WHERE movie_id = ? AND status = 'available'
                    """,
                    (movie_id,),
                ).fetchone()
                if has_available is None:
                    connection.execute(
                        "INSERT INTO movie_files (movie_id, status) VALUES (?, 'downloading')",
                        (movie_id,),
                    )
            return self._get_movie(connection, movie_id)

    def list_taste_tags(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT code, name AS label, category, sentiment, sort_order
                FROM tags
                WHERE code IS NOT NULL
                ORDER BY CASE category
                    WHEN 'viewing' THEN 1
                    WHEN 'emotion' THEN 2
                    WHEN 'strength' THEN 3
                    WHEN 'weakness' THEN 4
                    WHEN 'outcome' THEN 5
                    ELSE 6 END,
                    sort_order, id
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def import_draft(self, payload: MovieDraftImportRequest) -> dict[str, Any]:
        movie = payload.movie
        with self.database.connect() as connection:
            duplicate = connection.execute(
                "SELECT id FROM movies WHERE tmdb_id = ? OR imdb_id = ?",
                (movie.tmdb_id, movie.imdb_id),
            ).fetchone()
            if duplicate:
                raise MovieAlreadyExistsError("Movie already exists")

            cursor = connection.execute(
                """
                INSERT INTO movies (
                    title, original_title, release_year, tmdb_id, imdb_id,
                    runtime_minutes, original_language, overview, poster_url,
                    certification_country, certification_rating, imdb_rating,
                    tmdb_rating, is_new
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    movie.title,
                    movie.original_title,
                    movie.release_year,
                    movie.tmdb_id,
                    movie.imdb_id,
                    movie.runtime_minutes,
                    movie.original_language,
                    movie.overview or "",
                    str(movie.poster_url) if movie.poster_url else None,
                    movie.certification.country if movie.certification else None,
                    movie.certification.rating if movie.certification else None,
                    movie.imdb_rating,
                    movie.tmdb_rating,
                ),
            )
            movie_id = cursor.lastrowid

            for sort_order, genre in enumerate(movie.genres):
                connection.execute(
                    """
                    INSERT INTO genres (canonical_name, display_name)
                    VALUES (?, ?)
                    ON CONFLICT(canonical_name)
                    DO UPDATE SET display_name = excluded.display_name
                    """,
                    (genre.canonical_name, genre.display_name),
                )
                genre_id = connection.execute(
                    "SELECT id FROM genres WHERE canonical_name = ?",
                    (genre.canonical_name,),
                ).fetchone()["id"]
                connection.execute(
                    """
                    INSERT INTO movie_genres (movie_id, genre_id, sort_order)
                    VALUES (?, ?, ?)
                    """,
                    (movie_id, genre_id, sort_order),
                )

            for credit in movie.credits:
                connection.execute(
                    """
                    INSERT INTO movie_credits (
                        movie_id, person_id, canonical_name, display_name,
                        credit_type, sort_order
                    ) VALUES (?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        movie_id,
                        credit.canonical_name,
                        credit.display_name,
                        credit.credit_type,
                        credit.sort_order,
                    ),
                )

            for sort_order, company in enumerate(movie.production_companies):
                connection.execute(
                    """
                    INSERT INTO movie_production_companies (
                        movie_id, company_name, sort_order
                    ) VALUES (?, ?, ?)
                    """,
                    (movie_id, company, sort_order),
                )

            for source in payload.sources:
                connection.execute(
                    """
                    INSERT INTO movie_sources (
                        movie_id, source_name, source_url, checked_at, notes
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        movie_id,
                        source.source_name,
                        str(source.source_url),
                        source.checked_at.isoformat(),
                        ", ".join(source.supported_fields),
                    ),
                )

            connection.execute(
                """
                INSERT INTO movie_user_data (
                    movie_id, watched, personal_rating, comment, in_wishlist
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    movie_id,
                    int(payload.watched),
                    payload.personal_rating,
                    payload.comment,
                    int(payload.in_wishlist),
                ),
            )
            connection.execute(
                "INSERT INTO movie_files (movie_id, status) VALUES (?, ?)",
                (movie_id, payload.availability),
            )
            return self._get_movie(connection, movie_id)

    def update_user_data(
        self, movie_id: int, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        column_map = {
            "watched": "watched",
            "personal_rating": "personal_rating",
            "comment": "comment",
            "in_wishlist": "in_wishlist",
        }
        assignments: list[str] = []
        parameters: list[Any] = []
        tag_codes = changes.get("tag_codes")

        for field, value in changes.items():
            column = column_map.get(field)
            if column is None:
                continue
            assignments.append(f"{column} = ?")
            parameters.append(int(value) if isinstance(value, bool) else value)

        with self.database.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM movies WHERE id = ?", (movie_id,)
            ).fetchone()
            if exists is None:
                return None

            if assignments:
                assignments.append("updated_at = CURRENT_TIMESTAMP")
                parameters.append(movie_id)
                connection.execute(
                    f"UPDATE movie_user_data SET {', '.join(assignments)} "
                    "WHERE movie_id = ?",
                    parameters,
                )
            if tag_codes is not None:
                normalized_codes = list(dict.fromkeys(tag_codes))
                known_codes: set[str] = set()
                if normalized_codes:
                    placeholders = ", ".join("?" for _ in normalized_codes)
                    rows = connection.execute(
                        f"SELECT code FROM tags WHERE code IN ({placeholders})",
                        normalized_codes,
                    ).fetchall()
                    known_codes = {row["code"] for row in rows}
                unknown = set(normalized_codes) - known_codes
                if unknown:
                    raise UnknownTasteTagError(
                        f"Unknown taste tag codes: {', '.join(sorted(unknown))}"
                    )
                connection.execute(
                    """
                    DELETE FROM movie_tags
                    WHERE movie_id = ? AND tag_id IN (
                        SELECT id FROM tags WHERE code IS NOT NULL
                    )
                    """,
                    (movie_id,),
                )
                for code in normalized_codes:
                    connection.execute(
                        """
                        INSERT INTO movie_tags (movie_id, tag_id)
                        SELECT ?, id FROM tags WHERE code = ?
                        """,
                        (movie_id, code),
                    )
                connection.execute(
                    """
                    UPDATE movie_user_data
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE movie_id = ?
                    """,
                    (movie_id,),
                )
            return self._get_movie(connection, movie_id)

    def _get_movie(
        self, connection: sqlite3.Connection, movie_id: int
    ) -> dict[str, Any] | None:
        movie = connection.execute(
            """
            SELECT m.*, ud.watched, ud.personal_rating, ud.comment, ud.in_wishlist,
                   COALESCE(
                       (SELECT CASE
                           WHEN SUM(mf.status = 'available') > 0 THEN 'available'
                           WHEN SUM(mf.status = 'downloading') > 0 THEN 'downloading'
                           ELSE 'missing'
                       END FROM movie_files mf WHERE mf.movie_id = m.id),
                       'missing'
                   ) AS availability
            FROM movies m
            JOIN movie_user_data ud ON ud.movie_id = m.id
            WHERE m.id = ?
            """,
            (movie_id,),
        ).fetchone()
        if movie is None:
            return None

        genres = connection.execute(
            """
            SELECT g.id, g.canonical_name, g.display_name
            FROM movie_genres mg
            JOIN genres g ON g.id = mg.genre_id
            WHERE mg.movie_id = ?
            ORDER BY mg.sort_order, g.id
            """,
            (movie_id,),
        ).fetchall()
        credits = connection.execute(
            """
            SELECT id, person_id, canonical_name, display_name, credit_type,
                   sort_order, character, department, job
            FROM movie_credits
            WHERE movie_id = ?
            ORDER BY credit_type, sort_order, id
            """,
            (movie_id,),
        ).fetchall()
        companies = connection.execute(
            """
            SELECT company_name FROM movie_production_companies
            WHERE movie_id = ? ORDER BY sort_order, id
            """,
            (movie_id,),
        ).fetchall()
        sources = connection.execute(
            """
            SELECT source_name, source_url, checked_at, notes
            FROM movie_sources WHERE movie_id = ? ORDER BY id
            """,
            (movie_id,),
        ).fetchall()
        tags = connection.execute(
            """
            SELECT t.name, t.code FROM movie_tags mt
            JOIN tags t ON t.id = mt.tag_id
            WHERE mt.movie_id = ?
            ORDER BY t.category, t.sort_order, t.id
            """,
            (movie_id,),
        ).fetchall()

        result = dict(movie)
        result["genres"] = [dict(row) for row in genres]
        result["credits"] = [dict(row) for row in credits]
        result["production_companies"] = [row["company_name"] for row in companies]
        result["sources"] = [dict(row) for row in sources]
        result["user_data"] = {
            "watched": bool(movie["watched"]),
            "personal_rating": movie["personal_rating"],
            "comment": movie["comment"],
            "in_wishlist": bool(movie["in_wishlist"]),
            "tags": [row["name"] for row in tags],
            "tag_codes": [row["code"] for row in tags if row["code"]],
        }
        result["is_new"] = bool(movie["is_new"])
        return result
