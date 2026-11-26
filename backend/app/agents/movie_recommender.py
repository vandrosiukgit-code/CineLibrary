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
from app.repositories.movies import MovieRepository
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.schemas.recommendations import (
    GeminiRecommendationOutput,
    RecommendationMatch,
    RecommendationRequest,
    RecommendationResponse,
    TemporaryPerson,
    TemporaryRecommendation,
)
from app.services.movie_dna import MovieDNAService
from app.services.people_sync import PeopleSynchronizer
from app.services.recommendation_scoring import build_reference_profiles, score_recommendation
from app.services.taste_profile import TasteProfileBuilder


RECOMMENDATION_PROMPT = """
You are CineLibrary's personal movie recommendation agent.
Use only the supplied taste profile and current configurator request.
The taste profile describes evidence about movie preferences, not psychology.
Repeated high-confidence evidence is stronger than isolated signals.
Use requestMovieDNA before selecting candidates. Seek features in its seek list
and avoid features in its avoid list. Larger weights on the 0-1 scale indicate
stronger evidence from the current reference films. Resolve conflicts in favor of
the user's explicit wishes and constraints, then the current reference profile.
Use tasteProfile.movieDNASignals as a long-term preference when choosing among
films that fit the current request. Its viewingContext is the average across all
comparable watched films and indicates familiarity. The higher- and lower-rated
lists contain a signed rating adjustment (score) to averageRelevance, resulting
in weightedRelevance. Prefer repeated signals and treat them as associations
with whole-film ratings. Neutral and missing ratings contribute to familiarity.
Give greater weight to the user's explicit feedback about a characteristic.
Current-request wishes and constraints take priority over long-term preferences.
Never return a movie present in tasteProfile.doNotRecommend.
Return exactly requestedCount distinct feature films.

Return one JSON object and no Markdown:
{"movies":[{"title":"international release title from TMDB (en-US)","releaseYear":2020,"relevance":85,"reason":"Камерный детектив с сухим юмором подходит под ваш запрос.","wishMatches":{}}],"featureLabels":{}}

Use the complete request for candidate selection. Score relevance from 0 to 100
for the explicit wishes, genres and additional conditions for this session only.
When those are empty, score the overall fit as a fallback. The application compares
the reference films separately. For every reason, write one short sentence in natural Russian
(up to 240 characters). Name a concrete feature of the film and relate it to
the current request or a preference supported by the profile. Describe features
in everyday words and omit Movie DNA terminology, raw tags, internal field names,
and scores. Never claim a user liked a specific feature based on a whole-film
rating alone. When personal evidence is limited, explain how the film fits the request.
In featureLabels translate each referenceFeatures value into a short, natural
Russian phrase. Keep the input keys exactly and add no characteristics of your own.
Return an empty object if no referenceFeatures are supplied.
In wishMatches assess each item in wishCriteria under its exact input key. Its value
is a list of objects with label, score and detail. For a free-text wish, split it
into at most four distinct concrete preferences if needed. For structured genres
and constraints, return one object per input. Use natural Russian for labels and
details, a score from 0 to 100 for compliance, or null when evidence is missing.
For mandatory conditions use 100 when satisfied and 0 only for confirmed violations.
Only assess what the user explicitly requested. Exclude films you know violate a
mandatory condition. Do not put reference similarities into wishMatches.
Use real films only and use exactly the fields shown.
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
        movie_dna: MovieDNAService | None = None,
        movies: MovieRepository | None = None,
    ) -> None:
        self.brain = brain
        self.tmdb = tmdb
        self.librarian = librarian
        self.profile_builder = profile_builder
        self.people_repository = people_repository
        self.sessions = sessions
        self.movie_dna = movie_dna
        self.movies = movies
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
        reference_profiles = (
            build_reference_profiles(self.movie_dna, request.references)
            if self.movie_dna and request.references else {}
        )
        has_references = bool(request.references) or any(
            answer.card_id == "references" and answer.values and not answer.skipped
            for answer in request.answers
        )
        wish_criteria = {
            f"{card_index}-{value_index}": {"value": value.strip(), "cardId": answer.card_id}
            for card_index, answer in enumerate(request.answers)
            if answer.card_id != "references" and not answer.skipped
            for value_index, value in enumerate(answer.values) if value.strip()
        }
        has_wishes = bool(wish_criteria)
        prompt_payload = {
            "requestedCount": request.count,
            "tasteProfile": profile,
            "currentRequest": request.model_dump(by_alias=True),
            "wishCriteria": wish_criteria,
            "requestMovieDNA": {
                direction: [
                    {"feature": name, "weight": round(weight, 4)}
                    for name, weight in reference_profiles.get(relation, {}).values()
                ]
                for direction, relation in (("seek", "similar"), ("avoid", "avoid"))
            },
            "referenceFeatures": {
                str(tag_id): name
                for features in reference_profiles.values()
                for tag_id, (name, _) in features.items()
            },
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
                    max_output_tokens=8192 if has_wishes else 4096,
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
        excluded_tmdb_ids = {movie["tmdbId"] for movie in profile.get("doNotRecommend", [])}
        for index, suggestion in enumerate(output.movies, start=1):
            self._check_cancelled(is_cancelled)
            if any(
                (criterion["cardId"] == "constraints"
                 or criterion["value"].startswith(("Обязательно:", "Исключить:")))
                and suggestion.wish_matches.get(key)
                and suggestion.wish_matches[key][0].score == 0
                for key, criterion in wish_criteria.items()
            ):
                report(f"Фильм {index} исключён: нарушено обязательное условие.")
                continue
            report(
                f"Movie Librarian 1: обрабатываем фильм {index} из "
                f"{len(output.movies)} — {suggestion.title}."
            )
            movie_input = suggestion.title
            if suggestion.release_year:
                movie_input = f"{movie_input} ({suggestion.release_year})"
            librarian_result = self.librarian.research_movies([movie_input])[0]
            identification = librarian_result.identification
            if identification is None or identification.status != "identified":
                report(f"Фильм {index} исключён: TMDB ID не подтверждён.")
                continue
            tmdb_id = identification.tmdb_id
            if tmdb_id in excluded_tmdb_ids:
                report(f"Фильм {index} исключён: TMDB ID просмотрен или уже есть в подборе.")
                continue
            local_movie = self.movies.find_by_tmdb_id(tmdb_id) if self.movies else None
            if librarian_result.movie is not None:
                genre_names = {genre.display_name.casefold() for genre in librarian_result.movie.genres}
            else:
                genre_names = {genre["display_name"].casefold() for genre in (local_movie or {}).get("genres", [])}
            if any(
                criterion["cardId"] == "genres"
                and criterion["value"].startswith("Исключить:")
                and criterion["value"].partition(":")[2].strip().casefold() in genre_names
                for criterion in wish_criteria.values()
            ):
                report(f"Фильм {index} исключён: запрещённый жанр в карточке TMDB.")
                continue
            try:
                candidate = self.tmdb.get_movie_candidate(tmdb_id, language="en-US")
            except TMDBAPIError:
                report(f"Фильм {index} исключён: название недоступно в TMDB.")
                continue
            if candidate["tmdbId"] != tmdb_id or not candidate["title"]:
                report(f"Фильм {index} исключён: название не подтверждено в TMDB.")
                continue
            excluded_tmdb_ids.add(tmdb_id)
            suggestion = suggestion.model_copy(update={
                "title": candidate["title"],
                "original_title": candidate["originalTitle"],
                "release_year": candidate["releaseYear"] or identification.release_year,
            })
            people, people_bundles, credits, people_issues = self._temporary_people(
                tmdb_id,
                cancelled=is_cancelled,
            )
            report(
                f"Фильм {index} из {len(output.movies)}: "
                f"статус {librarian_result.status}, людей в карточке {len(people)}."
            )
            recommendation_id = uuid4().hex
            candidate_scores = {}
            if reference_profiles and self.movie_dna:
                genome = self.movie_dna.get(tmdb_id)
                if genome["status"] == "found":
                    candidate_scores = {
                        tag["tag_id"]: tag["relevance"] for tag in genome["tags"]
                    }
            wish_matches = []
            for key, criterion in wish_criteria.items():
                label = criterion["value"][:300]
                if criterion["cardId"] == "genres":
                    relation, _, genre = label.partition(":")
                    if relation == "Исключить":
                        continue
                    if relation == "Желательно":
                        if genre.strip().casefold() in genre_names:
                            wish_matches.append(RecommendationMatch(label=label, score=100))
                        continue
                assessments = suggestion.wish_matches.get(key, [])
                if not assessments:
                    wish_matches.append(RecommendationMatch(label=label))
                elif criterion["cardId"] == "wish":
                    wish_matches.extend(assessments[:4])
                else:
                    wish_matches.append(assessments[0].model_copy(update={"label": label}))
            relevance, explanation, breakdown = score_recommendation(
                suggestion, reference_profiles, candidate_scores, output.feature_labels,
                has_wishes=has_wishes, has_references=has_references,
                wish_matches=wish_matches,
            )
            public = TemporaryRecommendation(
                id=recommendation_id,
                tmdbId=tmdb_id,
                suggestion=suggestion.model_copy(update={"relevance": relevance}),
                status=librarian_result.status,
                movie=librarian_result.movie,
                existingMovieId=librarian_result.existing_movie_id,
                people=people,
                issues=[*librarian_result.issues, *people_issues],
                scoreExplanation=explanation,
                breakdown=breakdown,
                canRequestDownload=not local_movie or local_movie["availability"] != "available",
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

        public_recommendations.sort(key=lambda item: (item.breakdown.chef_pick, -item.suggestion.relevance))
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
