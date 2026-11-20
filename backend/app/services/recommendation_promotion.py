from __future__ import annotations

from app.repositories.movies import MovieRepository
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.schemas.recommendations import PromoteRecommendationResponse
from app.services.movie_download import MovieDownloadService


class RecommendationPromotionError(RuntimeError):
    pass


class RecommendationPromotionService:
    def __init__(
        self,
        *,
        movies: MovieRepository,
        sessions: RecommendationSessionStore,
        downloads: MovieDownloadService,
    ) -> None:
        self.movies = movies
        self.sessions = sessions
        self.downloads = downloads

    def promote(
        self, session_id: str, recommendation_id: str
    ) -> PromoteRecommendationResponse:
        return self.promote_many(session_id, [recommendation_id])[0]

    def promote_many(
        self, session_id: str, recommendation_ids: list[str]
    ) -> list[PromoteRecommendationResponse]:
        tmdb_ids = [
            self._tmdb_id(session_id, recommendation_id)
            for recommendation_id in dict.fromkeys(recommendation_ids)
        ]
        results = self.downloads.request_movies(tmdb_ids)
        return [
            PromoteRecommendationResponse(
                movie=result["movie"],
                downloadRequestId=result["download_request"]["id"],
            )
            for result in results
        ]

    def _tmdb_id(self, session_id: str, recommendation_id: str) -> int:
        stored = self.sessions.get_recommendation(session_id, recommendation_id)
        result = stored["librarian_result"]
        if result.status == "draft_ready" and result.movie is not None:
            return result.movie.tmdb_id
        if result.status == "already_exists" and result.existing_movie_id is not None:
            movie = self.movies.get_movie(result.existing_movie_id)
            if movie is not None and movie["tmdb_id"] is not None:
                return movie["tmdb_id"]
        raise RecommendationPromotionError(
            f"Recommendation cannot be promoted: {result.status}"
        )
