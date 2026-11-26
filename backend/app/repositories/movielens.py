from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from app.database import PROJECT_ROOT


DEFAULT_CSV_DIR = PROJECT_ROOT / "tag_genom"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "data" / "movielens.db"
DEFAULT_DATASET_VERSION = "movielens-25m"
INDEX_APPLICATION_ID = 0x434C4D4C

SCHEMA = """
CREATE TABLE dataset (version TEXT NOT NULL);
CREATE TABLE links (
    tmdb_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    PRIMARY KEY (tmdb_id, movie_id)
) WITHOUT ROWID;
CREATE TABLE tags (tag_id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE scores (
    movie_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL REFERENCES tags(tag_id),
    relevance REAL NOT NULL CHECK (relevance BETWEEN 0 AND 1),
    PRIMARY KEY (movie_id, tag_id)
) WITHOUT ROWID;
"""


@dataclass(frozen=True)
class GenomeTag:
    tag_id: int
    name: str
    relevance: float


@dataclass(frozen=True)
class OriginalGenomeResult:
    tmdb_id: int
    status: Literal[
        "found", "index_unavailable", "no_tmdb_mapping",
        "ambiguous_mapping", "no_original_genome",
    ]
    dataset_version: str | None = None
    movie_id: int | None = None
    source: Literal["original"] | None = None
    tags: tuple[GenomeTag, ...] = ()


def _csv_rows(path: Path, *fields: str) -> Iterator[tuple[str, ...]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        if next(reader, None) != list(fields):
            raise ValueError(f"Unexpected columns in {path.name}. Expected {', '.join(fields)}")
        for row in reader:
            if len(row) != len(fields):
                raise ValueError(f"Incorrect column count in {path.name}, line {reader.line_num}")
            yield tuple(row)


class MovieLensIndex:
    def __init__(self, path: Path = DEFAULT_INDEX_PATH) -> None:
        self.path = path

    def import_csv(self, csv_dir: Path, dataset_version: str) -> dict[str, int]:
        dataset_version = dataset_version.strip()
        if not dataset_version:
            raise ValueError("Dataset version must not be empty")
        if self.path.exists():
            uri = self.path.resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as existing:
                if existing.execute("PRAGMA application_id").fetchone()[0] != INDEX_APPLICATION_ID:
                    raise ValueError(f"Refusing to replace a non-MovieLens database: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Publish a complete index only after all three files have been validated and committed.
        with TemporaryDirectory(prefix="movielens-", dir=self.path.parent) as directory:
            staging = Path(directory) / "movielens.db"
            with closing(sqlite3.connect(staging)) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute(f"PRAGMA application_id = {INDEX_APPLICATION_ID}")
                connection.executescript(SCHEMA)
                with connection:
                    connection.execute("INSERT INTO dataset VALUES (?)", (dataset_version,))
                    links = connection.executemany(
                        "INSERT OR IGNORE INTO links VALUES (?, ?)",
                        (
                            (int(tmdb_id), int(movie_id))
                            for movie_id, _, tmdb_id in _csv_rows(
                                csv_dir / "links.csv", "movieId", "imdbId", "tmdbId"
                            )
                            if tmdb_id.strip()
                        ),
                    ).rowcount
                    tags = connection.executemany(
                        "INSERT INTO tags VALUES (?, ?)",
                        (
                            (int(tag_id), name)
                            for tag_id, name in _csv_rows(csv_dir / "genome-tags.csv", "tagId", "tag")
                        ),
                    ).rowcount
                    scores = connection.executemany(
                        "INSERT INTO scores VALUES (?, ?, ?)",
                        (
                            (int(movie_id), int(tag_id), float(relevance))
                            for movie_id, tag_id, relevance in _csv_rows(
                                csv_dir / "genome-scores.csv", "movieId", "tagId", "relevance"
                            )
                        ),
                    ).rowcount
                    if not all((links, tags, scores)):
                        raise ValueError("MovieLens import requires nonempty links, tags and scores")
                (genomes,) = connection.execute(
                    "SELECT count(*) FROM (SELECT DISTINCT movie_id FROM scores)"
                ).fetchone()
            staging.replace(self.path)
        return {"links": links, "tags": tags, "scores": scores, "genomes": genomes}

    def get_original(self, tmdb_id: int) -> OriginalGenomeResult:
        if tmdb_id <= 0:
            raise ValueError("TMDB ID must be positive")
        if not self.path.exists():
            return OriginalGenomeResult(tmdb_id, "index_unavailable")

        uri = self.path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            (version,) = connection.execute("SELECT version FROM dataset").fetchone()
            matches = connection.execute(
                "SELECT movie_id FROM links WHERE tmdb_id = ? LIMIT 2", (tmdb_id,)
            ).fetchall()
            if not matches:
                return OriginalGenomeResult(tmdb_id, "no_tmdb_mapping", version)
            if len(matches) > 1:
                return OriginalGenomeResult(tmdb_id, "ambiguous_mapping", version)
            (movie_id,) = matches[0]
            tags = tuple(
                GenomeTag(*row) for row in connection.execute(
                    """SELECT scores.tag_id, tags.name, scores.relevance
                       FROM scores JOIN tags USING (tag_id)
                       WHERE scores.movie_id = ? ORDER BY scores.tag_id""",
                    (movie_id,),
                )
            )
        if not tags:
            return OriginalGenomeResult(tmdb_id, "no_original_genome", version, movie_id)
        return OriginalGenomeResult(tmdb_id, "found", version, movie_id, "original", tags)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import and query the local MovieLens index.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    commands = parser.add_subparsers(dest="command", required=True)
    importer = commands.add_parser("import")
    importer.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    importer.add_argument("--dataset-version", default=DEFAULT_DATASET_VERSION)
    lookup = commands.add_parser("lookup")
    lookup.add_argument("tmdb_id", type=int)
    lookup.add_argument("--summary", action="store_true", help="Show the tag count only.")
    args = parser.parse_args()
    index = MovieLensIndex(args.index)

    try:
        if args.command == "import":
            result = index.import_csv(args.csv_dir, args.dataset_version)
            result["dataset_version"] = args.dataset_version.strip()
        else:
            result = asdict(index.get_original(args.tmdb_id))
            if args.summary:
                result["tag_count"] = len(result.pop("tags"))
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"MovieLens: {error}\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
