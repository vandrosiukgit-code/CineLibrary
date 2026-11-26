from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


CreditType = Literal["actor", "director", "producer", "writer", "composer"]
IdentificationStatus = Literal["identified", "ambiguous", "not_found"]
LibrarianStatus = Literal[
    "draft_ready", "already_exists", "ambiguous", "not_found", "failed"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class MovieResearchRequest(StrictModel):
    movies: list[str] = Field(min_length=1, max_length=10)
    mode: Literal["library", "recommendation"] = "library"

    @field_validator("movies")
    @classmethod
    def normalize_movies(cls, movies: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for movie in movies:
            value = movie.strip()
            if not value:
                raise ValueError("Movie names must not be empty")
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                normalized.append(value)
        return normalized


class IdentificationCandidate(StrictModel):
    tmdb_id: int = Field(alias="tmdbId", gt=0)
    original_title: str = Field(alias="originalTitle", min_length=1)
    release_year: int | None = Field(alias="releaseYear", ge=1888, le=2200)


class MovieIdentification(StrictModel):
    input_text: str = Field(alias="inputText", min_length=1)
    status: IdentificationStatus
    confidence: float = Field(ge=0, le=1)
    tmdb_id: int | None = Field(alias="tmdbId", gt=0)
    original_title: str | None = Field(alias="originalTitle")
    release_year: int | None = Field(alias="releaseYear", ge=1888, le=2200)
    reason: str = Field(min_length=1)
    candidates: list[IdentificationCandidate]

    @model_validator(mode="after")
    def validate_identification(self):
        if self.status == "identified":
            if self.tmdb_id is None or not self.original_title or self.release_year is None:
                raise ValueError("identified movies require TMDB ID, title and year")
            if self.confidence < 0.8:
                raise ValueError("identified movies require confidence of at least 0.8")
        elif self.tmdb_id is not None:
            raise ValueError("ambiguous and not_found results must not select a TMDB ID")
        return self


class LocalizedName(StrictModel):
    canonical_name: str = Field(alias="canonicalName", min_length=1)
    display_name: str = Field(alias="displayName", min_length=1)


class CertificationDraft(StrictModel):
    country: str = Field(min_length=2, max_length=2)
    rating: str = Field(min_length=1, max_length=20)


class MovieCreditDraft(LocalizedName):
    credit_type: CreditType = Field(alias="creditType")
    sort_order: int = Field(alias="sortOrder", ge=0)
    person_id: None = Field(alias="personId")


class MovieSourceDraft(StrictModel):
    source_name: str = Field(alias="sourceName", min_length=1)
    source_url: AnyHttpUrl = Field(alias="sourceUrl")
    checked_at: date = Field(alias="checkedAt")
    supported_fields: list[str] = Field(alias="supportedFields", min_length=1)


class MovieCardDraft(StrictModel):
    title: str = Field(min_length=1)
    original_title: str = Field(alias="originalTitle", min_length=1)
    release_year: int = Field(alias="releaseYear", ge=1888, le=2200)
    tmdb_id: int = Field(alias="tmdbId", gt=0)
    imdb_id: str | None = Field(alias="imdbId", pattern=r"^tt\d{7,10}$")
    runtime_minutes: int | None = Field(alias="runtimeMinutes", gt=0)
    countries: list[str]
    original_language: str | None = Field(alias="originalLanguage")
    certification: CertificationDraft | None
    genres: list[LocalizedName]
    overview: str | None
    credits: list[MovieCreditDraft]
    production_companies: list[str] = Field(alias="productionCompanies")
    tmdb_rating: float | None = Field(alias="tmdbRating", ge=0, le=10)
    imdb_rating: None = Field(alias="imdbRating")
    poster_url: AnyHttpUrl | None = Field(alias="posterUrl")

    @model_validator(mode="after")
    def validate_credits(self):
        if sum(credit.credit_type == "actor" for credit in self.credits) > 10:
            raise ValueError("No more than 10 principal actors are allowed")
        credit_keys = [
            (credit.canonical_name.casefold(), credit.credit_type)
            for credit in self.credits
        ]
        if len(credit_keys) != len(set(credit_keys)):
            raise ValueError("Duplicate movie credits are not allowed")
        return self


class MovieLibrarianResult(StrictModel):
    input_text: str = Field(alias="inputText", min_length=1)
    status: LibrarianStatus
    identification: MovieIdentification | None
    movie: MovieCardDraft | None
    existing_movie_id: int | None = Field(alias="existingMovieId")
    sources: list[MovieSourceDraft]
    issues: list[str]

    @model_validator(mode="after")
    def validate_result(self):
        if self.status == "draft_ready" and self.movie is None:
            raise ValueError("draft_ready results require a movie card")
        if self.status == "already_exists" and self.existing_movie_id is None:
            raise ValueError("already_exists results require an existing movie ID")
        if self.status in {"ambiguous", "not_found", "failed"} and self.movie:
            raise ValueError(f"{self.status} results must not contain a movie card")
        return self


class MovieResearchResponse(StrictModel):
    results: list[MovieLibrarianResult]


class MovieLibraryImportRequest(StrictModel):
    text: str = Field(min_length=1, max_length=20000)


class MovieLibraryImportItem(StrictModel):
    input_text: str = Field(alias="inputText")
    status: Literal["imported", "updated", "ambiguous", "not_found", "failed"]
    movie_id: int | None = Field(alias="movieId")
    title: str | None
    issues: list[str]
    candidates: list[IdentificationCandidate] = []


class MovieLibraryImportResult(StrictModel):
    items: list[MovieLibraryImportItem]


class MovieLibraryCandidateImportRequest(StrictModel):
    tmdb_ids: list[int] = Field(alias="tmdbIds", min_length=1, max_length=20)


class MovieLibraryImportJobLog(StrictModel):
    sequence: int
    created_at: str = Field(alias="createdAt")
    message: str


class MovieLibraryImportJobRead(StrictModel):
    job_id: str = Field(alias="jobId")
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    logs: list[MovieLibraryImportJobLog]
    result: MovieLibraryImportResult | None = None
    error: str | None = None
