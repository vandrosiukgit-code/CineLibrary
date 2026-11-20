from __future__ import annotations

from app.clients.tmdb import TMDBClient
from app.repositories.movies import MovieRepository
from app.repositories.people import PeopleRepository
from app.schemas.movies import MovieDraftImportRequest
from app.services.movie_card_builder import MovieCardBuilder
from app.services.people_sync import PeopleSynchronizer
from app.services.telegram_delivery import (
    TelegramConfigurationError,
    TelegramDeliveryService,
    build_movie_file_name,
)


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

    def request_movies(self, tmdb_ids: list[int]) -> list[dict]:
        if not self.telegram.get_settings()["configured"]:
            raise TelegramConfigurationError("Telegram-бот не настроен")
        unique_ids = list(dict.fromkeys(tmdb_ids))
        prepared = [self._prepare_movie(tmdb_id) for tmdb_id in unique_ids]
        message_id = self.telegram.send_movies(
            [(item["international_title"], item["file_name"]) for item in prepared]
        )
        return [
            {
                "movie": item["movie"],
                "download_request": self.movies.create_download_request(
                    tmdb_movie_id=item["movie"]["tmdb_id"],
                    local_movie_id=item["movie"]["id"],
                    title=item["movie"]["title"],
                    international_title=item["international_title"],
                    file_name=item["file_name"],
                    telegram_message_id=message_id,
                ),
            }
            for item in prepared
        ]

    def _prepare_movie(self, tmdb_id: int) -> dict:
        movie = self.movies.find_by_tmdb_id(tmdb_id)
        if movie is None:
            card, sources = self.builder.build(self.tmdb.get_movie_bundle(tmdb_id))
            movie = self.movies.import_draft(
                MovieDraftImportRequest(
                    movie=card,
                    sources=sources,
                    watched=False,
                    personalRating=None,
                    comment="",
                    inWishlist=True,
                    availability="downloading",
                )
            )
        else:
            self.movies.update_user_data(movie["id"], {"in_wishlist": True})
            movie = self.movies.mark_downloading(movie["id"])
        self.people_sync.sync_movie(movie["id"], tmdb_id)
        refreshed = self.movies.get_movie(movie["id"])
        international_title = refreshed["original_title"] or refreshed["title"]
        return {
            "movie": refreshed,
            "international_title": international_title,
            "file_name": build_movie_file_name(refreshed["id"], international_title),
        }
