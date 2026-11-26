import json
from contextlib import closing
from typing import Any
from uuid import uuid4

from app.database import MovieDatabase


class MovieDNARepository:
    def __init__(self, database: MovieDatabase) -> None:
        self.database = database

    def get(
        self, tmdb_id: int, dataset_version: str, algorithm_version: str
    ) -> dict[str, Any] | None:
        with closing(self.database.connect()) as connection:
            row = connection.execute(
                """
                SELECT result_json, claim_until > unixepoch() AS active
                FROM movie_dna_estimates
                WHERE tmdb_id = ? AND dataset_version = ? AND algorithm_version = ?
                """,
                (tmdb_id, dataset_version, algorithm_version),
            ).fetchone()
        if row is None:
            return None
        if row["result_json"] is not None:
            return json.loads(row["result_json"])
        return {"tmdb_id": tmdb_id, "status": "in_progress"} if row["active"] else None

    def claim(self, tmdb_id: int, dataset_version: str, algorithm_version: str) -> str | None:
        token = uuid4().hex
        with closing(self.database.connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO movie_dna_estimates (
                    tmdb_id, dataset_version, algorithm_version, claim_token, claim_until
                ) VALUES (?, ?, ?, ?, unixepoch() + 1800)
                ON CONFLICT (tmdb_id, dataset_version, algorithm_version) DO UPDATE
                    SET claim_token = excluded.claim_token, claim_until = excluded.claim_until
                    WHERE movie_dna_estimates.result_json IS NULL
                      AND movie_dna_estimates.claim_until <= unixepoch()
                """,
                (tmdb_id, dataset_version, algorithm_version, token),
            )
            return token if cursor.rowcount else None

    def save(self, token: str, result: dict[str, Any]) -> None:
        with closing(self.database.connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE movie_dna_estimates
                SET result_json = ?, claim_token = NULL, claim_until = NULL
                WHERE tmdb_id = ? AND dataset_version = ? AND algorithm_version = ?
                  AND claim_token = ?
                """,
                (
                    json.dumps(result, ensure_ascii=False, allow_nan=False),
                    result["tmdb_id"], result["dataset_version"], result["algorithm_version"],
                    token,
                ),
            )
            if not cursor.rowcount:
                raise RuntimeError("Movie DNA claim was lost")

    def release(self, tmdb_id: int, dataset_version: str, algorithm_version: str, token: str) -> None:
        with closing(self.database.connect()) as connection, connection:
            connection.execute(
                """
                DELETE FROM movie_dna_estimates
                WHERE tmdb_id = ? AND dataset_version = ? AND algorithm_version = ?
                  AND claim_token = ?
                """,
                (tmdb_id, dataset_version, algorithm_version, token),
            )
