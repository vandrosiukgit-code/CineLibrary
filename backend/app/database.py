from __future__ import annotations

import os
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "movies.db"
SQL_DIR = Path(__file__).resolve().parent / "sql"


def resolve_database_path() -> Path:
    configured_path = os.getenv("CINELIBRARY_MOVIE_DB")
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


class MovieDatabase:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else resolve_database_path()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema = (SQL_DIR / "001_initial_schema.sql").read_text(encoding="utf-8")
        seed = (SQL_DIR / "test_seed.sql").read_text(encoding="utf-8")

        with self.connect() as connection:
            connection.executescript(schema)
            movie_count = connection.execute(
                "SELECT COUNT(*) FROM movies"
            ).fetchone()[0]
            if movie_count == 0:
                connection.executescript(seed)
