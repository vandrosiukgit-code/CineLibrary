import json
import logging
import re
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from threading import Event, Lock, Thread

from app.repositories.movies import MovieRepository
from app.services.library_import import LibraryImportService
from app.services.media_scan import MediaCopy, scan_media


sync_lock = Lock()
logger = logging.getLogger(__name__)
MEDIA_SYNC_INTERVAL_SECONDS = 15 * 60


def read_media_sync_settings(movies: MovieRepository) -> dict:
    with movies.database.connect() as connection:
        row = connection.execute("SELECT root, excluded FROM media_sync_settings WHERE id = 1").fetchone()
    return {"root": row["root"], "excluded": json.loads(row["excluded"])} if row else {"root": "", "excluded": []}


class MediaSyncScheduler:
    def __init__(self, movies: MovieRepository) -> None:
        self.movies = movies
        self.stopped = Event()
        self.worker: Thread | None = None

    def start(self) -> None:
        # The manual route holds sync_lock while activating the scheduler.
        if self.worker is None:
            self.worker = Thread(target=self._run, name="media-sync", daemon=True)
            self.worker.start()

    def stop(self) -> None:
        self.stopped.set()

    def _run(self) -> None:
        while not self.stopped.wait(MEDIA_SYNC_INTERVAL_SECONDS):
            if not sync_lock.acquire(blocking=False):
                continue
            try:
                settings = read_media_sync_settings(self.movies)
                if settings["root"]:
                    result = sync_media(self.movies, Path(settings["root"]), tuple(map(Path, settings["excluded"])))
                    if result["errors"]:
                        logger.warning("Media availability check could not read %d paths", len(result["errors"]))
            except Exception:
                logger.exception("Automatic media availability check failed")
            finally:
                sync_lock.release()


def sync_media(
    movies: MovieRepository, root: Path, excluded: tuple[Path, ...],
    create_importer: Callable[[], LibraryImportService] | None = None,
) -> dict:
    root = root.resolve()
    scan = scan_media(root, excluded=excluded)
    if scan.errors:
        return {"matched": 0, "pending": [], "errors": scan.errors}

    def normalize(title: str) -> str:
        return " ".join(re.sub(r"[_.]+", " ", title).casefold().split())

    with movies.database.connect() as connection:
        catalog = connection.execute("SELECT id, title, original_title, release_year FROM movies").fetchall()
        linked = {str(Path(row["file_path"])): row["movie_id"] for row in connection.execute(
            "SELECT file_path, movie_id FROM movie_files WHERE scan_root = ?", (str(root),),
        )}
    ids = {row["id"] for row in catalog}
    titles = defaultdict(set)
    for row in catalog:
        for title in (row["title"], row["original_title"]):
            if title:
                titles[normalize(title)].add((row["id"], row["release_year"]))

    matched: list[tuple[MediaCopy, int]] = []
    unmatched: dict[str, list[MediaCopy]] = defaultdict(list)
    pending = []
    for copy in scan.copies:
        if copy.status == "unknown":
            pending.append(copy.name)
            continue
        path = Path(copy.path)
        if copy.cl_id:
            movie_id = int(copy.cl_id.partition("-")[2])
            if movie_id in ids:
                matched.append((copy, movie_id))
            else:
                pending.append(copy.name)
            continue
        if copy.path in linked:
            matched.append((copy, linked[copy.path]))
            continue
        name = path.name
        if copy.kind in {"video", "iso"}:
            name = Path(re.sub(r"\.!qb$", "", name, flags=re.IGNORECASE)).stem
        name = " ".join(re.sub(r"[_.]+", " ", name).split())
        year_match = re.fullmatch(r"(.+?)[ (]+((?:18|19|20)\d{2})\)?", name)
        title, year = (year_match[1], int(year_match[2])) if year_match else (name, None)
        candidates = {movie_id for movie_id, release_year in titles[normalize(title)] if year is None or year == release_year}
        if len(candidates) == 1:
            matched.append((copy, next(iter(candidates))))
        elif candidates or not name or copy.status != "available":
            pending.append(copy.name)
        else:
            unmatched[name].append(copy)

    def save_copies(connection, copies):
        connection.executemany(
            "DELETE FROM movie_files WHERE movie_id = ? AND file_path IS NULL AND scan_root IS NULL AND status = 'downloading'",
            ((movie_id,) for copy, movie_id in copies if copy.status == "available"),
        )
        connection.executemany(
            "INSERT INTO movie_files (movie_id, file_path, file_name, file_format, status, scan_root) VALUES (?, ?, ?, ?, ?, ?)",
            ((movie_id, copy.path, copy.name, copy.kind, copy.status, str(root)) for copy, movie_id in copies),
        )

    with movies.database.connect() as connection:
        # Keep the last known data for copies that could not be classified this time.
        retained = {copy.path for copy in scan.copies if copy.status == "unknown"}
        obsolete = set(linked) - retained
        connection.executemany("DELETE FROM movie_files WHERE scan_root = ? AND file_path = ?",
                               ((str(root), path) for path in obsolete))
        save_copies(connection, matched)

    if create_importer is None:
        pending.extend(copy.name for copies in unmatched.values() for copy in copies)
    elif unmatched:
        imported = create_importer().run(
            list(unmatched), lambda _: None, lambda: False, mark_existing_watched=False,
        )
        imported_copies = []
        for item in imported["items"]:
            for copy in unmatched[item["input_text"]]:
                if item["movie_id"] is None:
                    pending.append(copy.name)
                else:
                    imported_copies.append((copy, item["movie_id"]))
        with movies.database.connect() as connection:
            save_copies(connection, imported_copies)
        matched.extend(imported_copies)
    return {"matched": len(matched), "pending": pending, "errors": {}}
