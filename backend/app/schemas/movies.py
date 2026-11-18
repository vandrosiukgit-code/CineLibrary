from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AvailabilityStatus = Literal["available", "downloading", "missing"]


class GenreRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    canonical_name: str = Field(serialization_alias="canonicalName")
    display_name: str = Field(serialization_alias="displayName")


class CreditRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    person_id: int | None = Field(serialization_alias="personId")
    canonical_name: str = Field(serialization_alias="canonicalName")
    display_name: str = Field(serialization_alias="displayName")
    credit_type: str = Field(serialization_alias="creditType")
    sort_order: int = Field(serialization_alias="sortOrder")


class SourceRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_name: str = Field(serialization_alias="sourceName")
    source_url: str = Field(serialization_alias="sourceUrl")
    checked_at: str = Field(serialization_alias="checkedAt")
    notes: str | None


class UserDataRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    watched: bool
    personal_rating: int | None = Field(serialization_alias="personalRating")
    comment: str
    in_wishlist: bool = Field(serialization_alias="inWishlist")
    tags: list[str]


class UserDataUpdate(BaseModel):
    watched: bool | None = None
    personal_rating: int | None = Field(default=None, alias="personalRating", ge=1, le=5)
    comment: str | None = Field(default=None, max_length=4000)
    in_wishlist: bool | None = Field(default=None, alias="inWishlist")


class MovieRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    title: str
    original_title: str = Field(serialization_alias="originalTitle")
    release_year: int = Field(serialization_alias="releaseYear")
    tmdb_id: int | None = Field(serialization_alias="tmdbId")
    imdb_id: str | None = Field(serialization_alias="imdbId")
    runtime_minutes: int | None = Field(serialization_alias="runtimeMinutes")
    original_language: str | None = Field(serialization_alias="originalLanguage")
    overview: str
    poster_url: str | None = Field(serialization_alias="posterUrl")
    certification_country: str | None = Field(serialization_alias="certificationCountry")
    certification_rating: str | None = Field(serialization_alias="certificationRating")
    imdb_rating: float | None = Field(serialization_alias="imdbRating")
    is_new: bool = Field(serialization_alias="isNew")
    genres: list[GenreRead]
    credits: list[CreditRead]
    production_companies: list[str] = Field(serialization_alias="productionCompanies")
    sources: list[SourceRead]
    availability: AvailabilityStatus
    user_data: UserDataRead = Field(serialization_alias="userData")
