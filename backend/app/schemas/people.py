from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PersonFilmographyRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tmdb_movie_id: int = Field(serialization_alias="tmdbMovieId")
    local_movie_id: int | None = Field(serialization_alias="localMovieId")
    credit_kind: str = Field(serialization_alias="creditKind")
    title: str
    original_title: str = Field(serialization_alias="originalTitle")
    release_year: int | None = Field(serialization_alias="releaseYear")
    character: str | None
    department: str | None
    job: str | None
    poster_url: str | None = Field(serialization_alias="posterUrl")
    vote_average: float | None = Field(serialization_alias="voteAverage")
    in_library: bool = Field(serialization_alias="inLibrary")


class PersonRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    tmdb_id: int = Field(serialization_alias="tmdbId")
    name: str
    display_name: str = Field(serialization_alias="displayName")
    also_known_as: list[str] = Field(serialization_alias="alsoKnownAs")
    biography: str
    birthday: str | None
    deathday: str | None
    place_of_birth: str | None = Field(serialization_alias="placeOfBirth")
    gender: int | None
    known_for_department: str | None = Field(
        serialization_alias="knownForDepartment"
    )
    profile_url: str | None = Field(serialization_alias="profileUrl")
    homepage: str | None
    imdb_id: str | None = Field(serialization_alias="imdbId")
    wikidata_id: str | None = Field(serialization_alias="wikidataId")
    last_refreshed_at: str = Field(serialization_alias="lastRefreshedAt")
    next_refresh_at: str = Field(serialization_alias="nextRefreshAt")
    filmography: list[PersonFilmographyRead]


class PeopleSyncResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    movies_processed: int = Field(serialization_alias="moviesProcessed")
    people_created: int = Field(serialization_alias="peopleCreated")
    people_refreshed: int = Field(serialization_alias="peopleRefreshed")
    people_skipped: int = Field(serialization_alias="peopleSkipped")
    links_updated: int = Field(serialization_alias="linksUpdated")
    failures: list[str]
