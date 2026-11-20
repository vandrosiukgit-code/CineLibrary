from pydantic import BaseModel, ConfigDict, Field


class APICredentialsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    replicate_api_token: str | None = Field(
        default=None, alias="replicateApiToken", min_length=1
    )
    tmdb_read_access_token: str | None = Field(
        default=None, alias="tmdbReadAccessToken", min_length=1
    )


class APICredentialsRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    replicate_configured: bool = Field(serialization_alias="replicateConfigured")
    tmdb_configured: bool = Field(serialization_alias="tmdbConfigured")
    updated_at: str | None = Field(serialization_alias="updatedAt")
