from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

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
from app.services.people_sync import PeopleSynchronizer
from app.services.recommendation_jobs import RecommendationJobNotFoundError


router = APIRouter(prefix="/api/agents/movie-librarian-1", tags=["agents"])


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
