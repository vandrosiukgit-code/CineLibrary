from fastapi import APIRouter, HTTPException, Request

from app.agents.movie_librarian import MovieLibrarian
from app.clients.replicate_gemini import (
    ReplicateConfigurationError,
    ReplicateGeminiClient,
)
from app.clients.tmdb import TMDBClient, TMDBConfigurationError
from app.schemas.movie_research import MovieResearchRequest, MovieResearchResponse


router = APIRouter(prefix="/api/agents/movie-librarian-1", tags=["agents"])


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
