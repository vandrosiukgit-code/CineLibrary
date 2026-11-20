from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.agents.movie_librarian import MovieLibrarian
from app.clients.replicate_gemini import ReplicateGeminiClient
from app.clients.tmdb import TMDBAPIError, TMDBClient
from app.core.cancellation import OperationCancelled
from app.repositories.people import PeopleRepository
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.schemas.recommendations import (
    GeminiRecommendationOutput,
    RecommendationRequest,
    RecommendationResponse,
    TemporaryPerson,
    TemporaryRecommendation,
)
from app.services.people_sync import PeopleSynchronizer
from app.services.taste_profile import TasteProfileBuilder


RECOMMENDATION_PROMPT = """
You are CineLibrary's personal movie recommendation agent.
Use only the supplied taste profile and current configurator request.
The taste profile describes evidence about movie preferences, not psychology.
Repeated high-confidence evidence is stronger than isolated signals.
Current-request constraints take priority over long-term preferences.
Never return a movie present in tasteProfile.doNotRecommend.
Return exactly requestedCount distinct feature films.

Return one JSON object and no Markdown:
{"movies":[{"title":"localized or widely recognizable title","originalTitle":"native title or null","releaseYear":2020,"relevance":85}]}

relevance is your subjective 0-100 estimate of how well the film matches this
specific request. It is the only recommendation commentary. Do not add reasons,
descriptions, explanations, or fields outside the schema. Use real films only.
Provide a release year whenever known so Movie Librarian 1 can identify the film.
""".strip()


class MovieRecommenderOutputError(RuntimeError):
    pass


class MovieRecommender:
    def __init__(
        self,
        *,
        brain: ReplicateGeminiClient,
        tmdb: TMDBClient,
        librarian: MovieLibrarian,
        profile_builder: TasteProfileBuilder,
        people_repository: PeopleRepository,
        sessions: RecommendationSessionStore,
    ) -> None:
        self.brain = brain
        self.tmdb = tmdb
        self.librarian = librarian
        self.profile_builder = profile_builder
        self.people_repository = people_repository
        self.sessions = sessions
        self.people_selector = PeopleSynchronizer(tmdb, people_repository)

    def recommend(
        self,
        request: RecommendationRequest,
        progress: Callable[[str], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> RecommendationResponse:
        report = progress or (lambda _message: None)
        is_cancelled = cancelled or (lambda: False)
        self._check_cancelled(is_cancelled)
        report("Формируем профиль вкуса по просмотренной библиотеке.")
        profile = self.profile_builder.build()
        report(
            "Профиль готов: "
            f"{profile.get('summary', {}).get('watchedMovies', 0)} просмотренных фильмов."
        )
        prompt_payload = {
            "requestedCount": request.count,
            "tasteProfile": profile,
            "currentRequest": request.model_dump(by_alias=True),
        }
        prompt = json.dumps(prompt_payload, ensure_ascii=False, indent=2)
        self._check_cancelled(is_cancelled)
        report(
            f"Отправляем Gemini запрос на {request.count} рекомендаций."
        )
        try:
            output = GeminiRecommendationOutput.model_validate(
                self.brain.generate_json(
                    RECOMMENDATION_PROMPT,
                    prompt_payload,
                    temperature=0.35,
                    max_output_tokens=4096,
                )
            )
        except ValidationError as error:
            raise MovieRecommenderOutputError(
                "Gemini returned an invalid recommendation list"
            ) from error
        if len(output.movies) != request.count:
            raise MovieRecommenderOutputError(
                f"Gemini returned {len(output.movies)} movies; expected {request.count}"
            )
        report(f"Gemini вернул {len(output.movies)} фильмов.")

        stored_recommendations: list[dict[str, Any]] = []
        public_recommendations: list[TemporaryRecommendation] = []
        for index, suggestion in enumerate(output.movies, start=1):
            self._check_cancelled(is_cancelled)
            report(
                f"Movie Librarian 1: обрабатываем фильм {index} из "
                f"{len(output.movies)} — {suggestion.title}."
            )
            movie_input = suggestion.original_title or suggestion.title
            if suggestion.release_year:
                movie_input = f"{movie_input} ({suggestion.release_year})"
            librarian_result = self.librarian.research_movies([movie_input])[0]
            people, people_bundles, credits, people_issues = self._temporary_people(
                librarian_result.identification.tmdb_id
                if librarian_result.identification
                and librarian_result.identification.status == "identified"
                else None,
                cancelled=is_cancelled,
            )
            report(
                f"Фильм {index} из {len(output.movies)}: "
                f"статус {librarian_result.status}, людей в карточке {len(people)}."
            )
            recommendation_id = uuid4().hex
            public = TemporaryRecommendation(
                id=recommendation_id,
                suggestion=suggestion,
                status=librarian_result.status,
                movie=librarian_result.movie,
                existingMovieId=librarian_result.existing_movie_id,
                people=people,
                issues=[*librarian_result.issues, *people_issues],
            )
            public_recommendations.append(public)
            stored_recommendations.append(
                {
                    "id": recommendation_id,
                    "public": public,
                    "librarian_result": librarian_result,
                    "people_bundles": people_bundles,
                    "credits": credits,
                }
            )

        session_id = self.sessions.create(
            profile=profile,
            prompt=prompt,
            recommendations=stored_recommendations,
        )
        report("Временный каталог рекомендаций сформирован.")
        return RecommendationResponse(
            sessionId=session_id,
            tasteProfile=profile,
            prompt=prompt,
            movies=public_recommendations,
        )

    def _temporary_people(
        self,
        tmdb_movie_id: int | None,
        *,
        cancelled: Callable[[], bool],
    ) -> tuple[
        list[TemporaryPerson],
        dict[int, dict[str, Any]],
        list[dict[str, Any]],
        list[str],
    ]:
        if tmdb_movie_id is None:
            return [], {}, [], []
        issues: list[str] = []
        bundles: dict[int, dict[str, Any]] = {}
        people: list[TemporaryPerson] = []
        try:
            credits = self.people_selector.selected_credits(
                self.tmdb.get_movie_credits(tmdb_movie_id)
            )
        except TMDBAPIError as error:
            return [], {}, [], [str(error)]

        for credit in credits:
            self._check_cancelled(cancelled)
            tmdb_person_id = credit["tmdb_person_id"]
            existing = self.people_repository.find_by_tmdb_id(tmdb_person_id)
            if existing is not None:
                people.append(
                    TemporaryPerson(
                        tmdbId=tmdb_person_id,
                        name=existing["name"],
                        displayName=existing["display_name"],
                        profileUrl=existing["profile_url"],
                        inPeopleDatabase=True,
                    )
                )
                continue
            try:
                bundle = self.tmdb.get_person_bundle(tmdb_person_id)
            except TMDBAPIError as error:
                issues.append(f"Person {tmdb_person_id}: {error}")
                continue
            bundles[tmdb_person_id] = bundle
            translations = bundle.get("translations") or {}
            russian = next(
                (
                    item.get("data") or {}
                    for item in translations.get("translations", [])
                    if item.get("iso_639_1") == "ru"
                ),
                {},
            )
            profile_path = bundle.get("profile_path")
            people.append(
                TemporaryPerson(
                    tmdbId=tmdb_person_id,
                    name=bundle.get("name") or credit["name"],
                    displayName=russian.get("name") or bundle.get("name") or credit["name"],
                    profileUrl=(
                        f"https://image.tmdb.org/t/p/h632{profile_path}"
                        if profile_path
                        else None
                    ),
                    inPeopleDatabase=False,
                )
            )
        return people, bundles, credits, issues

    @staticmethod
    def _check_cancelled(cancelled: Callable[[], bool]) -> None:
        if cancelled():
            raise OperationCancelled()
