from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.tmdb import TMDBConfigurationError, TMDBClient
from app.repositories.people import PeopleRepository
from app.schemas.people import PeopleSyncResult, PersonRead
from app.services.people_sync import PeopleSynchronizer


router = APIRouter(prefix="/api/people", tags=["people"])


def get_repository(request: Request) -> PeopleRepository:
    return request.app.state.people_repository


@router.get("/{person_id}", response_model=PersonRead, response_model_by_alias=True)
def get_person(person_id: int, request: Request):
    person = get_repository(request).get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.post(
    "/sync",
    response_model=PeopleSyncResult,
    response_model_by_alias=True,
)
def sync_people(
    request: Request,
    movie_id: Annotated[int | None, Query(alias="movieId", gt=0)] = None,
):
    try:
        tmdb = TMDBClient.from_environment()
    except TMDBConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    repository = get_repository(request)
    synchronizer = PeopleSynchronizer(tmdb, repository)
    if movie_id is None:
        return synchronizer.sync_all()
    movie = repository.get_movie_target(movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return synchronizer.sync_movie(movie["id"], movie["tmdb_id"])
