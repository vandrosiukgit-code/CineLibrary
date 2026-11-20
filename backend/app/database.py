from __future__ import annotations

import os
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "movies.db"
SQL_DIR = Path(__file__).resolve().parent / "sql"


def unicode_casefold(value: str | None) -> str:
    return value.casefold() if value is not None else ""


def resolve_database_path() -> Path:
    configured_path = os.getenv("CINELIBRARY_MOVIE_DB")
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


class MovieDatabase:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else resolve_database_path()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.create_function(
            "CASEFOLD", 1, unicode_casefold, deterministic=True
        )
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            for migration_path in sorted(SQL_DIR.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(migration_path.name.split("_", 1)[0])
                if self._migration_applied(connection, version):
                    continue
                connection.executescript(migration_path.read_text(encoding="utf-8"))

    def seed(self, seed_path: Path | str) -> None:
        with self.connect() as connection:
            connection.executescript(Path(seed_path).read_text(encoding="utf-8"))

    @staticmethod
    def _migration_applied(
        connection: sqlite3.Connection, version: int
    ) -> bool:
        table_exists = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_migrations'
            """
        ).fetchone()
        if not table_exists:
            return False
        return connection.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
        ).fetchone() is not None
