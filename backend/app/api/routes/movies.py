from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.repositories.movies import MovieRepository
from app.schemas.movies import MovieRead, UserDataUpdate


router = APIRouter(prefix="/api/movies", tags=["movies"])


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
):
    return get_repository(request).list_movies(
        search=search,
        watched=watched,
        in_wishlist=in_wishlist,
        availability=availability,
        genre=genre,
    )


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
    movie = get_repository(request).update_user_data(
        movie_id, payload.model_dump(exclude_unset=True)
    )
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
