from fastapi import APIRouter, HTTPException, Request

from app.schemas.settings import APICredentialsRead, APICredentialsUpdate
from app.services.api_credentials import APICredentialsError


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get(
    "/api-credentials",
    response_model=APICredentialsRead,
    response_model_by_alias=True,
)
def get_api_credentials(request: Request):
    return request.app.state.api_credentials.get_settings()


@router.put(
    "/api-credentials",
    response_model=APICredentialsRead,
    response_model_by_alias=True,
)
def save_api_credentials(payload: APICredentialsUpdate, request: Request):
    try:
        return request.app.state.api_credentials.save(
            payload.replicate_api_token,
            payload.tmdb_read_access_token,
        )
    except APICredentialsError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
