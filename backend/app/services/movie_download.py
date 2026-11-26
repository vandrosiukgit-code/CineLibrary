from __future__ import annotations

from app.clients.tmdb import TMDBAPIError, TMDBClient
from app.repositories.movies import MovieRepository
from app.repositories.people import PeopleRepository
from app.schemas.movies import MovieDraftImportRequest
from app.services.movie_card_builder import MovieCardBuilder
from app.services.people_sync import PeopleSynchronizer
from app.services.telegram_delivery import (
    TelegramConfigurationError,
    TelegramDeliveryError,
    TelegramDeliveryService,
    build_movie_file_name,
)


class PartialMovieDownloadError(TelegramDeliveryError):
    def __init__(self, message: str, delivered_tmdb_ids: list[int]) -> None:
        super().__init__(message)
        self.delivered_tmdb_ids = delivered_tmdb_ids


class MovieDownloadService:
    def __init__(
        self,
        *,
        movies: MovieRepository,
        people: PeopleRepository,
        tmdb: TMDBClient,
        telegram: TelegramDeliveryService,
    ) -> None:
        self.movies = movies
        self.tmdb = tmdb
        self.telegram = telegram
        self.people_sync = PeopleSynchronizer(tmdb, people)
        self.builder = MovieCardBuilder()

    def request_movies(self, tmdb_ids: list[int], *, prefer_posters: bool = False) -> list[dict]:
        if not self.telegram.get_settings()["configured"]:
            raise TelegramConfigurationError("Telegram-бот не настроен")
        unique_ids = list(dict.fromkeys(tmdb_ids))
        prepared = [
            self._prepare_movie(tmdb_id, include_countries=len(unique_ids) == 1)
            for tmdb_id in unique_ids
        ]
        messages = [(item["movie"], item["file_name"]) for item in prepared]
        results = {}
        try:
            for index, message_id in self.telegram.send_movie_requests(messages, prefer_posters=prefer_posters):
                item = prepared[index]
                movie = item["movie"]
                request = self.movies.create_download_request(
                    tmdb_movie_id=movie["tmdb_id"],
                    local_movie_id=movie["id"],
                    title=movie["title"],
                    international_title=item["international_title"],
                    file_name=item["file_name"],
                    telegram_message_id=message_id,
                )
                results[index] = {"movie": movie, "download_request": request}
        except TelegramDeliveryError as error:
            if results:
                raise PartialMovieDownloadError(
                    f"Telegram подтвердил доставку {len(results)} из {len(prepared)} фильмов. {error}",
                    [result["movie"]["tmdb_id"] for result in results.values()],
                ) from error
            raise
        return [results[index] for index in range(len(prepared))]

    def _prepare_movie(self, tmdb_id: int, *, include_countries: bool) -> dict:
        movie = self.movies.find_by_tmdb_id(tmdb_id)
        countries = []
        if movie is None:
            card, sources = self.builder.build(self.tmdb.get_movie_bundle(tmdb_id))
            countries = card.countries
            movie = self.movies.import_draft(
                MovieDraftImportRequest(
                    movie=card,
                    sources=sources,
                    watched=False,
                )
            )
        elif include_countries:
            try:
                bundle = self.tmdb.get_movie_bundle(tmdb_id)
            except TMDBAPIError:
                pass
            else:
                if bundle["localized"].get("id") == tmdb_id:
                    countries = [
                        country["name"]
                        for country in bundle["english"].get("production_countries", [])
                        if country.get("name")
                    ]
        self.people_sync.sync_movie(movie["id"], tmdb_id)
        refreshed = self.movies.get_movie(movie["id"])
        if countries:
            refreshed["countries"] = countries
        international_title = refreshed["original_title"] or refreshed["title"]
        return {
            "movie": refreshed,
            "international_title": international_title,
            "file_name": build_movie_file_name(refreshed["id"], international_title),
        }
