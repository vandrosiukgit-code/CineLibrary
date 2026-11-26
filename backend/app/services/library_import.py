from __future__ import annotations

import re
from collections.abc import Callable

from app.agents.movie_librarian import MovieLibrarian
from app.core.cancellation import OperationCancelled
from app.repositories.movies import MovieRepository
from app.schemas.movies import MovieDraftImportRequest
from app.services.movie_card_builder import MovieCardBuilder
from app.services.people_sync import PeopleSynchronizer


class LibraryImportInputError(ValueError):
    pass


def parse_movie_list(text: str) -> list[str]:
    movies: list[str] = []
    for raw_line in re.split(r"[\r\n;]+", text):
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if line and line.casefold() not in {item.casefold() for item in movies}:
            movies.append(line)
    if not movies:
        raise LibraryImportInputError("Список фильмов пуст")
    if len(movies) > 20:
        raise LibraryImportInputError("За один раз можно добавить не более 20 фильмов")
    return movies


class LibraryImportService:
    def __init__(
        self,
        *,
        librarian: MovieLibrarian | None,
        movies: MovieRepository,
        people_sync: PeopleSynchronizer,
    ) -> None:
        self.librarian = librarian
        self.movies = movies
        self.people_sync = people_sync
        self.builder = MovieCardBuilder()

    def run(
        self,
        movie_inputs: list[str],
        progress: Callable[[str], None],
        cancelled: Callable[[], bool],
    ) -> dict:
        if self.librarian is None:
            raise RuntimeError("Movie Librarian is required for text import")
        items: list[dict] = []
        total = len(movie_inputs)
        for index, movie_input in enumerate(movie_inputs, start=1):
            if cancelled():
                raise OperationCancelled()
            progress(f"Определяем фильм {index} из {total}: {movie_input}")
            result = self.librarian.research_movies([movie_input])[0]
            if result.status == "draft_ready" and result.movie is not None:
                movie = self.movies.import_draft(
                    MovieDraftImportRequest(
                        movie=result.movie,
                        sources=result.sources,
                        watched=True,
                        availability="missing",
                    )
                )
                status = "imported"
            elif result.status == "already_exists" and result.existing_movie_id:
                movie = self.movies.update_user_data(
                    result.existing_movie_id, {"watched": True}
                )
                status = "updated"
            else:
                items.append(
                    {
                        "input_text": movie_input,
                        "status": result.status,
                        "movie_id": None,
                        "title": None,
                        "issues": result.issues,
                        "candidates": (
                            [candidate.model_dump() for candidate in result.identification.candidates]
                            if result.identification is not None
                            else []
                        ),
                    }
                )
                progress(f"Не удалось добавить: {movie_input}")
                continue
            if cancelled():
                raise OperationCancelled()
            self.people_sync.sync_movie(movie["id"], movie["tmdb_id"])
            items.append(
                {
                    "input_text": movie_input,
                    "status": status,
                    "movie_id": movie["id"],
                    "title": movie["title"],
                    "issues": [],
                    "candidates": [],
                }
            )
            progress(f"Добавлен фильм: {movie['title']}")
        return {"items": items}

    def import_candidates(
        self,
        tmdb_ids: list[int],
        progress: Callable[[str], None],
        cancelled: Callable[[], bool],
    ) -> dict:
        items: list[dict] = []
        unique_ids = list(dict.fromkeys(tmdb_ids))
        for index, tmdb_id in enumerate(unique_ids, start=1):
            if cancelled():
                raise OperationCancelled()
            progress(f"Добавляем выбранный фильм {index} из {len(unique_ids)}")
            existing = self.movies.find_by_tmdb_id(tmdb_id)
            if existing is None:
                card, sources = self.builder.build(
                    self.people_sync.tmdb.get_movie_bundle(tmdb_id)
                )
                movie = self.movies.import_draft(
                    MovieDraftImportRequest(
                        movie=card,
                        sources=sources,
                        watched=True,
                        availability="missing",
                    )
                )
                status = "imported"
            else:
                movie = self.movies.update_user_data(existing["id"], {"watched": True})
                status = "updated"
            if cancelled():
                raise OperationCancelled()
            self.people_sync.sync_movie(movie["id"], tmdb_id)
            items.append(
                {
                    "input_text": movie["title"],
                    "status": status,
                    "movie_id": movie["id"],
                    "title": movie["title"],
                    "issues": [],
                    "candidates": [],
                }
            )
            progress(f"Добавлен фильм: {movie['title']}")
        return {"items": items}
