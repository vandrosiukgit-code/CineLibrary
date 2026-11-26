from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.movie_research import MovieCardDraft
from app.schemas.movies import MovieRead


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ConfiguratorAnswer(StrictModel):
    card_id: str = Field(alias="cardId", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    values: list[str] = Field(max_length=50)
    skipped: bool = False


class ReferenceMovie(StrictModel):
    tmdb_id: int = Field(alias="tmdbId", gt=0)
    relation: Literal["similar", "avoid"]


class RecommendationRequest(StrictModel):
    count: int = Field(default=5, ge=1, le=10)
    answers: list[ConfiguratorAnswer] = Field(min_length=1, max_length=10)
    references: list[ReferenceMovie] = Field(default_factory=list)


class SuggestedMovie(StrictModel):
    title: str = Field(min_length=1, max_length=300)
    original_title: str | None = Field(default=None, alias="originalTitle")
    release_year: int | None = Field(default=None, alias="releaseYear", ge=1888, le=2200)
    relevance: int = Field(ge=0, le=100)
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class RecommendationMatch(StrictModel):
    label: str = Field(min_length=1, max_length=300)
    score: int | None = Field(default=None, ge=0, le=100)
    detail: str = Field(default="", max_length=240)


class GeminiSuggestedMovie(SuggestedMovie):
    wish_matches: dict[str, list[RecommendationMatch]] = Field(default_factory=dict, alias="wishMatches")


class RecommendationBreakdown(StrictModel):
    chef_pick: bool = Field(alias="chefPick")
    wish_score: int | None = Field(alias="wishScore", ge=0, le=100)
    reference_score: int | None = Field(alias="referenceScore", ge=0, le=100)
    matches: list[RecommendationMatch]
    summary: str


class TemporaryPerson(StrictModel):
    tmdb_id: int = Field(alias="tmdbId", gt=0)
    name: str
    display_name: str = Field(alias="displayName")
    profile_url: str | None = Field(alias="profileUrl")
    in_people_database: bool = Field(alias="inPeopleDatabase")


class TemporaryRecommendation(StrictModel):
    id: str
    tmdb_id: int | None = Field(default=None, alias="tmdbId")
    suggestion: SuggestedMovie
    status: Literal["draft_ready", "already_exists", "ambiguous", "not_found", "failed"]
    movie: MovieCardDraft | None
    existing_movie_id: int | None = Field(alias="existingMovieId")
    people: list[TemporaryPerson]
    issues: list[str]
    score_explanation: str | None = Field(default=None, alias="scoreExplanation")
    breakdown: RecommendationBreakdown | None = None
    can_request_download: bool = Field(default=True, alias="canRequestDownload")


class RecommendationResponse(StrictModel):
    session_id: str = Field(alias="sessionId")
    taste_profile: dict[str, Any] = Field(alias="tasteProfile")
    prompt: str
    movies: list[TemporaryRecommendation]


class RecommendationJobLog(StrictModel):
    sequence: int = Field(ge=1)
    created_at: str = Field(alias="createdAt")
    message: str


class RecommendationJobRead(StrictModel):
    job_id: str = Field(alias="jobId")
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    logs: list[RecommendationJobLog]
    result: RecommendationResponse | None = None
    error: str | None = None


class PromoteRecommendationRequest(StrictModel):
    recommendation_id: str = Field(alias="recommendationId", min_length=1)


class PromoteRecommendationsRequest(StrictModel):
    recommendation_ids: list[str] = Field(
        alias="recommendationIds", min_length=1, max_length=5
    )


class PromoteRecommendationResponse(StrictModel):
    movie: MovieRead
    download_request_id: int = Field(alias="downloadRequestId")


class PromoteRecommendationsResponse(StrictModel):
    results: list[PromoteRecommendationResponse]


class GeminiRecommendationOutput(StrictModel):
    movies: list[GeminiSuggestedMovie]
    feature_labels: dict[int, str] = Field(default_factory=dict, alias="featureLabels")
