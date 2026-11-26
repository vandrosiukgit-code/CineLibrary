import json
import os
from pathlib import Path as LocalPath
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel, Field

from app.agents.movie_librarian import MovieLibrarian
from app.clients.replicate_gemini import (
    ReplicateAPIError,
    ReplicateConfigurationError,
    ReplicateGeminiClient,
)
from app.clients.tmdb import TMDBAPIError, TMDBClient, TMDBConfigurationError
from app.schemas.movie_research import (
    MovieLibraryImportJobRead,
    MovieLibraryCandidateImportRequest,
    MovieLibraryImportRequest,
    MovieResearchRequest,
    MovieResearchResponse,
)
from app.services.library_import import (
    LibraryImportInputError,
    LibraryImportService,
    parse_movie_list,
)
from app.services.movie_dna import MovieDNAError, MovieDNAService
from app.services.media_sync import read_media_sync_settings, sync_lock, sync_media
from app.services.people_sync import PeopleSynchronizer
from app.services.recommendation_jobs import RecommendationJobNotFoundError


router = APIRouter(prefix="/api/agents/movie-librarian-1", tags=["agents"])


class MediaSyncSettings(BaseModel):
    root: str = Field(max_length=4096)
    excluded: list[str] = Field(default_factory=list, max_length=100)


@router.get("/media-sync/folders")
def browse_media_folders(path: str | None = None):
    if path is None:
        roots = os.listdrives() if os.name == "nt" else ["/"]
        return {"path": None, "parent": None, "folders": [{"name": root, "path": root} for root in roots]}
    directory = LocalPath(path)
    if not directory.is_absolute():
        raise HTTPException(status_code=422, detail="Укажите полный путь к папке.")
    try:
        directory = directory.resolve()
        with os.scandir(directory) as entries:
            folders = [
                {"name": entry.name, "path": entry.path}
                for entry in entries
                if entry.is_dir(follow_symlinks=False) and not LocalPath(entry.path).is_junction()
            ]
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail="Папка недоступна для просмотра.") from error
    return {
        "path": str(directory),
        "parent": str(directory.parent) if directory.parent != directory else None,
        "folders": sorted(folders, key=lambda entry: entry["name"].casefold()),
    }


@router.get("/media-sync/settings", response_model=MediaSyncSettings)
def get_media_sync_settings(request: Request):
    return read_media_sync_settings(request.app.state.movie_repository)


@router.put("/media-sync/settings", response_model=MediaSyncSettings)
def save_media_sync_settings(payload: MediaSyncSettings, request: Request):
    root = payload.root.strip()
    if root and not LocalPath(root).is_absolute():
        raise HTTPException(status_code=422, detail="Укажите полный путь к папке на компьютере с CineLibrary.")
    try:
        excluded = []
        if root:
            resolved = LocalPath(root).resolve()
            root = str(resolved)
            excluded = [str((resolved / value.strip()).resolve()) for value in payload.excluded if value.strip()]
            if any(LocalPath(path) == resolved or not LocalPath(path).is_relative_to(resolved) for path in excluded):
                raise ValueError("Укажите исключения внутри папки медиатеки.")
            if not resolved.is_dir() or any(not LocalPath(path).is_dir() for path in excluded):
                raise ValueError("Выберите существующие папки.")
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Дождитесь завершения синхронизации.")
    try:
        with request.app.state.movie_repository.database.connect() as connection:
            connection.execute(
                "INSERT INTO media_sync_settings VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET root = excluded.root, excluded = excluded.excluded",
                (root, json.dumps(excluded)),
            )
    finally:
        sync_lock.release()
    return {"root": root, "excluded": excluded}


@router.post("/media-sync")
def run_media_sync(request: Request):
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Синхронизация уже запущена.")
    try:
        settings = get_media_sync_settings(request)
        if not settings["root"]:
            raise HTTPException(status_code=409, detail="Сначала укажите папку медиатеки в боковом меню.")
        request.app.state.media_sync_scheduler.start()
        movies = request.app.state.movie_repository

        def create_importer() -> LibraryImportService:
            tmdb = TMDBClient.from_environment()
            return LibraryImportService(
                librarian=MovieLibrarian(brain=ReplicateGeminiClient.from_environment(), tmdb=tmdb,
                                         repository=movies, mode="library"),
                movies=movies,
                people_sync=PeopleSynchronizer(tmdb, request.app.state.people_repository),
            )

        return sync_media(movies, LocalPath(settings["root"]), tuple(map(LocalPath, settings["excluded"])), create_importer)
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        sync_lock.release()


def build_movie_dna_service(request: Request) -> MovieDNAService:
    return MovieDNAService.from_database(request.app.state.movie_repository.database)


@router.get("/movie-dna/{tmdb_id}")
def get_movie_dna(tmdb_id: Annotated[int, Path(gt=0)], request: Request):
    return build_movie_dna_service(request).get(tmdb_id)


@router.post("/movie-dna/{tmdb_id}/estimate")
def estimate_movie_dna(tmdb_id: Annotated[int, Path(gt=0)], request: Request):
    movie = request.app.state.movie_repository.find_by_tmdb_id(tmdb_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Фильм не найден в каталоге")
    try:
        return build_movie_dna_service(request).estimate(
            movie,
            create_brain=ReplicateGeminiClient.from_environment,
            create_tmdb=TMDBClient.from_environment,
        )
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ReplicateAPIError, TMDBAPIError, MovieDNAError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/research",
    response_model=MovieResearchResponse,
    response_model_by_alias=True,
)
def research_movies(payload: MovieResearchRequest, request: Request):
    try:
        librarian = MovieLibrarian(
            brain=ReplicateGeminiClient.from_environment(),
            tmdb=TMDBClient.from_environment(),
            repository=request.app.state.movie_repository,
            mode=payload.mode,
        )
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return MovieResearchResponse(results=librarian.research_movies(payload.movies))


@router.post(
    "/library-import/jobs",
    response_model=MovieLibraryImportJobRead,
    response_model_by_alias=True,
    status_code=202,
)
def start_library_import(payload: MovieLibraryImportRequest, request: Request):
    try:
        movie_inputs = parse_movie_list(payload.text)
        brain = ReplicateGeminiClient.from_environment()
        tmdb = TMDBClient.from_environment()
    except LibraryImportInputError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    def run(progress, cancelled):
        librarian = MovieLibrarian(
            brain=brain,
            tmdb=tmdb,
            repository=request.app.state.movie_repository,
            mode="library",
            cancelled=cancelled,
        )
        return LibraryImportService(
            librarian=librarian,
            movies=request.app.state.movie_repository,
            people_sync=PeopleSynchronizer(
                tmdb, request.app.state.people_repository
            ),
        ).run(movie_inputs, progress, cancelled)

    return request.app.state.library_import_jobs.start(run)


@router.post(
    "/library-import/candidates/jobs",
    response_model=MovieLibraryImportJobRead,
    response_model_by_alias=True,
    status_code=202,
)
def start_candidate_import(
    payload: MovieLibraryCandidateImportRequest, request: Request
):
    try:
        tmdb = TMDBClient.from_environment()
    except TMDBConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    def run(progress, cancelled):
        return LibraryImportService(
            librarian=None,
            movies=request.app.state.movie_repository,
            people_sync=PeopleSynchronizer(
                tmdb, request.app.state.people_repository
            ),
        ).import_candidates(payload.tmdb_ids, progress, cancelled)

    return request.app.state.library_import_jobs.start(run)


@router.get(
    "/library-import/jobs/{job_id}",
    response_model=MovieLibraryImportJobRead,
    response_model_by_alias=True,
)
def get_library_import(job_id: str, request: Request):
    try:
        return request.app.state.library_import_jobs.get(job_id)
    except RecommendationJobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Import job not found") from error


@router.post(
    "/library-import/jobs/{job_id}/cancel",
    response_model=MovieLibraryImportJobRead,
    response_model_by_alias=True,
)
def cancel_library_import(job_id: str, request: Request):
    try:
        return request.app.state.library_import_jobs.cancel(job_id)
    except RecommendationJobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Import job not found") from error
