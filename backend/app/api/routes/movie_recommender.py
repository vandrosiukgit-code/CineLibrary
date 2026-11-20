from fastapi import APIRouter, HTTPException, Request

from app.agents.movie_librarian import MovieLibrarian
from app.agents.movie_recommender import (
    MovieRecommender,
    MovieRecommenderOutputError,
)
from app.clients.replicate_gemini import (
    ReplicateAPIError,
    ReplicateConfigurationError,
    ReplicateGeminiClient,
)
from app.clients.tmdb import TMDBAPIError, TMDBClient, TMDBConfigurationError
from app.repositories.recommendation_sessions import (
    RecommendationSessionNotFoundError,
)
from app.services.recommendation_jobs import RecommendationJobNotFoundError
from app.schemas.recommendations import (
    PromoteRecommendationRequest,
    PromoteRecommendationResponse,
    PromoteRecommendationsRequest,
    PromoteRecommendationsResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationJobRead,
)
from app.services.recommendation_promotion import (
    RecommendationPromotionError,
    RecommendationPromotionService,
)
from app.services.taste_profile import TasteProfileBuilder
from app.services.telegram_delivery import (
    TelegramConfigurationError,
    TelegramDeliveryError,
)
from app.services.movie_download import MovieDownloadService


router = APIRouter(prefix="/api/agents/movie-recommender", tags=["agents"])


def build_promotion_service(request: Request) -> RecommendationPromotionService:
    tmdb = TMDBClient.from_environment()
    return RecommendationPromotionService(
        movies=request.app.state.movie_repository,
        sessions=request.app.state.recommendation_sessions,
        downloads=MovieDownloadService(
            movies=request.app.state.movie_repository,
            people=request.app.state.people_repository,
            tmdb=tmdb,
            telegram=request.app.state.telegram_delivery,
        ),
    )


def build_recommender(
    request: Request,
    *,
    cancelled=None,
) -> MovieRecommender:
    brain = ReplicateGeminiClient.from_environment()
    tmdb = TMDBClient.from_environment()
    librarian = MovieLibrarian(
        brain=brain,
        tmdb=tmdb,
        repository=request.app.state.movie_repository,
        mode="recommendation",
        cancelled=cancelled,
    )
    return MovieRecommender(
        brain=brain,
        tmdb=tmdb,
        librarian=librarian,
        profile_builder=TasteProfileBuilder(request.app.state.movie_repository),
        people_repository=request.app.state.people_repository,
        sessions=request.app.state.recommendation_sessions,
    )


@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    response_model_by_alias=True,
)
def recommend_movies(payload: RecommendationRequest, request: Request):
    try:
        return build_recommender(request).recommend(payload)
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ReplicateAPIError, TMDBAPIError, MovieRecommenderOutputError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/recommend/jobs",
    response_model=RecommendationJobRead,
    response_model_by_alias=True,
    status_code=202,
)
def start_recommendation_job(payload: RecommendationRequest, request: Request):
    try:
        # Validate credentials before returning a job ID.
        ReplicateGeminiClient.from_environment()
        TMDBClient.from_environment()
    except (ReplicateConfigurationError, TMDBConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    def run(progress, cancelled):
        return build_recommender(
            request,
            cancelled=cancelled,
        ).recommend(payload, progress=progress, cancelled=cancelled)

    return request.app.state.recommendation_jobs.start(run)


@router.get(
    "/recommend/jobs/{job_id}",
    response_model=RecommendationJobRead,
    response_model_by_alias=True,
)
def get_recommendation_job(job_id: str, request: Request):
    try:
        return request.app.state.recommendation_jobs.get(job_id)
    except RecommendationJobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Recommendation job not found") from error


@router.post(
    "/recommend/jobs/{job_id}/cancel",
    response_model=RecommendationJobRead,
    response_model_by_alias=True,
)
def cancel_recommendation_job(job_id: str, request: Request):
    try:
        return request.app.state.recommendation_jobs.cancel(job_id)
    except RecommendationJobNotFoundError as error:
        raise HTTPException(status_code=404, detail="Recommendation job not found") from error


@router.post(
    "/sessions/{session_id}/promote",
    response_model=PromoteRecommendationResponse,
    response_model_by_alias=True,
)
def promote_recommendation(
    session_id: str,
    payload: PromoteRecommendationRequest,
    request: Request,
):
    try:
        service = build_promotion_service(request)
        return service.promote(session_id, payload.recommendation_id)
    except RecommendationSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Recommendation not found") from error
    except (TMDBConfigurationError, TelegramConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except TelegramDeliveryError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (RecommendationPromotionError, TMDBAPIError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/sessions/{session_id}/promote-many",
    response_model=PromoteRecommendationsResponse,
    response_model_by_alias=True,
)
def promote_recommendations(
    session_id: str,
    payload: PromoteRecommendationsRequest,
    request: Request,
):
    try:
        results = build_promotion_service(request).promote_many(
            session_id, payload.recommendation_ids
        )
        return {"results": results}
    except RecommendationSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Recommendation not found") from error
    except (TMDBConfigurationError, TelegramConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except TelegramDeliveryError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (RecommendationPromotionError, TMDBAPIError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
