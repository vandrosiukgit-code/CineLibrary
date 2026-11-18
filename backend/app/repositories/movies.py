from __future__ import annotations

import sqlite3
from typing import Any

from app.database import MovieDatabase


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
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []

        if search:
            clauses.append("(m.title LIKE ? OR m.original_title LIKE ?)")
            pattern = f"%{search}%"
            parameters.extend((pattern, pattern))
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

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT m.id
            FROM movies m
            JOIN movie_user_data ud ON ud.movie_id = m.id
            {where}
            ORDER BY m.release_year DESC, m.title
        """

        with self.database.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
            return [self._get_movie(connection, row["id"]) for row in rows]

    def get_movie(self, movie_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            return self._get_movie(connection, movie_id)

    def find_by_tmdb_id(self, tmdb_id: int) -> dict[str, Any] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_id,)
            ).fetchone()
            return self._get_movie(connection, row["id"]) if row else None

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
            SELECT id, person_id, canonical_name, display_name, credit_type, sort_order
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
            SELECT t.name FROM movie_tags mt
            JOIN tags t ON t.id = mt.tag_id
            WHERE mt.movie_id = ? ORDER BY t.id
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
        }
        result["is_new"] = bool(movie["is_new"])
        return result
