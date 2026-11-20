import logging
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from app.clients.tmdb import TMDBConfigurationError, TMDBClient
from app.repositories.movies import (
    MovieAlreadyExistsError,
    MovieRepository,
    UnknownTasteTagError,
)
from app.services.people_sync import PeopleSynchronizer
from app.schemas.movies import (
    DownloadRequestCreate,
    DownloadRequestRead,
    MovieDraftImportRequest,
    MovieRead,
    MovieDownloadResult,
    TMDBDownloadRequestCreate,
    TasteTagRead,
    TelegramSettingsRead,
    TelegramSettingsUpdate,
    TelegramTestRead,
    UserDataUpdate,
)
from app.services.telegram_delivery import (
    TelegramConfigurationError,
    TelegramDeliveryError,
)
from app.services.movie_download import MovieDownloadService
from app.services.movie_card_builder import MovieCardBuilderError


router = APIRouter(prefix="/api/movies", tags=["movies"])
logger = logging.getLogger(__name__)


def sync_movie_people(
    synchronizer: PeopleSynchronizer, movie_id: int, tmdb_id: int
) -> None:
    try:
        synchronizer.sync_movie(movie_id, tmdb_id)
    except Exception:
        logger.exception("Automatic people sync failed for movie %s", movie_id)


def get_repository(request: Request) -> MovieRepository:
    return request.app.state.movie_repository


@router.get("", response_model=list[MovieRead], response_model_by_alias=True)
def list_movies(
    request: Request,
    search: Annotated[str | None, Query(max_length=200)] = None,
    watched: bool | None = None,
    in_wishlist: bool | None = Query(default=None, alias="inWishlist"),
    availability: Literal["available", "downloading", "missing"] | None = None,
    genre: str | None = None,
    personal_rating_min: Annotated[
        int | None, Query(alias="personalRatingMin", ge=1, le=5)
    ] = None,
    personal_rating_max: Annotated[
        int | None, Query(alias="personalRatingMax", ge=1, le=5)
    ] = None,
    has_personal_rating: bool | None = Query(
        default=None, alias="hasPersonalRating"
    ),
    has_taste_tags: bool | None = Query(default=None, alias="hasTasteTags"),
    tag_code: str | None = Query(default=None, alias="tagCode", max_length=100),
    sort: Literal[
        "release_desc", "release_asc", "title_asc", "rating_desc"
    ] = "release_desc",
):
    return get_repository(request).list_movies(
        search=search,
        watched=watched,
        in_wishlist=in_wishlist,
        availability=availability,
        genre=genre,
        personal_rating_min=personal_rating_min,
        personal_rating_max=personal_rating_max,
        has_personal_rating=has_personal_rating,
        has_taste_tags=has_taste_tags,
        tag_code=tag_code,
        sort=sort,
    )


@router.post(
    "/import",
    response_model=MovieRead,
    response_model_by_alias=True,
    status_code=201,
)
def import_movie(
    payload: MovieDraftImportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    try:
        movie = get_repository(request).import_draft(payload)
    except MovieAlreadyExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    try:
        tmdb = TMDBClient.from_environment()
    except TMDBConfigurationError:
        return movie
    background_tasks.add_task(
        sync_movie_people,
        PeopleSynchronizer(tmdb, request.app.state.people_repository),
        movie["id"],
        movie["tmdb_id"],
    )
    return movie


@router.get(
    "/taste-tags",
    response_model=list[TasteTagRead],
    response_model_by_alias=True,
)
def list_taste_tags(request: Request):
    return get_repository(request).list_taste_tags()


@router.get("/genres", response_model=list[str])
def list_genres(request: Request, watched: bool | None = None):
    return get_repository(request).list_genres(watched=watched)


@router.get(
    "/download-requests",
    response_model=list[DownloadRequestRead],
    response_model_by_alias=True,
)
def list_download_requests(request: Request):
    return get_repository(request).list_download_requests()


@router.post(
    "/download-requests",
    response_model=DownloadRequestRead,
    response_model_by_alias=True,
    status_code=201,
)
def create_download_request(payload: DownloadRequestCreate, request: Request):
    return get_repository(request).create_download_request(
        tmdb_movie_id=payload.tmdb_movie_id,
        local_movie_id=payload.local_movie_id,
        title=payload.title,
    )


@router.post(
    "/download-requests/by-tmdb",
    response_model=list[MovieDownloadResult],
    response_model_by_alias=True,
    status_code=201,
)
def create_download_requests_by_tmdb(
    payload: TMDBDownloadRequestCreate, request: Request
):
    try:
        tmdb = TMDBClient.from_environment()
        return MovieDownloadService(
            movies=request.app.state.movie_repository,
            people=request.app.state.people_repository,
            tmdb=tmdb,
            telegram=request.app.state.telegram_delivery,
        ).request_movies(payload.tmdb_movie_ids)
    except (TMDBConfigurationError, TelegramConfigurationError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (TMDBAPIError, TelegramDeliveryError, MovieCardBuilderError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get(
    "/telegram-settings",
    response_model=TelegramSettingsRead,
    response_model_by_alias=True,
)
def get_telegram_settings(request: Request):
    return request.app.state.telegram_delivery.get_settings()


@router.put(
    "/telegram-settings",
    response_model=TelegramSettingsRead,
    response_model_by_alias=True,
)
def save_telegram_settings(payload: TelegramSettingsUpdate, request: Request):
    try:
        return request.app.state.telegram_delivery.save_settings(
            payload.bot_token, payload.chat_id
        )
    except TelegramConfigurationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/telegram-settings/test",
    response_model=TelegramTestRead,
    response_model_by_alias=True,
)
def test_telegram_settings(request: Request):
    try:
        return {"message_id": request.app.state.telegram_delivery.send_test()}
    except TelegramConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except TelegramDeliveryError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/{movie_id}", response_model=MovieRead, response_model_by_alias=True)
def get_movie(movie_id: int, request: Request):
    movie = get_repository(request).get_movie(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.patch(
    "/{movie_id}/user-data",
    response_model=MovieRead,
    response_model_by_alias=True,
)
def update_user_data(movie_id: int, payload: UserDataUpdate, request: Request):
    try:
        movie = get_repository(request).update_user_data(
            movie_id, payload.model_dump(exclude_unset=True)
        )
    except UnknownTasteTagError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
