from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.movie_research import MovieCardDraft, MovieSourceDraft


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
    character: str | None = None
    department: str | None = None
    job: str | None = None


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
    tag_codes: list[str] = Field(serialization_alias="tagCodes")


class TasteTagRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    label: str
    category: str
    sentiment: int
    sort_order: int = Field(serialization_alias="sortOrder")


class DownloadRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tmdb_movie_id: int = Field(alias="tmdbMovieId", gt=0)
    local_movie_id: int | None = Field(default=None, alias="localMovieId", gt=0)
    title: str = Field(min_length=1, max_length=500)


class DownloadRequestRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    tmdb_movie_id: int = Field(serialization_alias="tmdbMovieId")
    local_movie_id: int | None = Field(serialization_alias="localMovieId")
    title: str
    international_title: str | None = Field(serialization_alias="internationalTitle")
    file_name: str | None = Field(serialization_alias="fileName")
    telegram_message_id: int | None = Field(serialization_alias="telegramMessageId")
    status: str
    requested_at: str = Field(serialization_alias="requestedAt")


class TMDBDownloadRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tmdb_movie_ids: list[int] = Field(
        alias="tmdbMovieIds", min_length=1, max_length=20
    )
    prefer_posters: bool = Field(default=False, alias="preferPosters")


class TelegramSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bot_token: str | None = Field(default=None, alias="botToken", min_length=1)
    chat_id: str = Field(alias="chatId", min_length=1, max_length=100)


class TelegramSettingsRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    configured: bool
    chat_id: str | None = Field(serialization_alias="chatId")
    updated_at: str | None = Field(serialization_alias="updatedAt")


class TelegramChatDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bot_token: str | None = Field(default=None, alias="botToken", min_length=1)


class TelegramChatRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    chat_id: str = Field(serialization_alias="chatId")
    label: str


class TelegramTestRead(BaseModel):
    message_id: int = Field(serialization_alias="messageId")


class UserDataUpdate(BaseModel):
    watched: bool | None = None
    personal_rating: int | None = Field(default=None, alias="personalRating", ge=1, le=5)
    comment: str | None = Field(default=None, max_length=4000)
    in_wishlist: bool | None = Field(default=None, alias="inWishlist")
    tag_codes: list[str] | None = Field(
        default=None, alias="tagCodes", max_length=32
    )


class MovieDraftImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    movie: MovieCardDraft
    sources: list[MovieSourceDraft]
    watched: bool = True
    personal_rating: int | None = Field(
        default=None, alias="personalRating", ge=1, le=5
    )
    comment: str = Field(default="", max_length=4000)
    in_wishlist: bool = Field(default=False, alias="inWishlist")
    availability: AvailabilityStatus = "missing"


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
    tmdb_rating: float | None = Field(serialization_alias="tmdbRating")
    is_new: bool = Field(serialization_alias="isNew")
    genres: list[GenreRead]
    credits: list[CreditRead]
    production_companies: list[str] = Field(serialization_alias="productionCompanies")
    sources: list[SourceRead]
    availability: AvailabilityStatus
    user_data: UserDataRead = Field(serialization_alias="userData")


class MovieDownloadResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    movie: MovieRead
    download_request: DownloadRequestRead = Field(
        serialization_alias="downloadRequest"
    )
