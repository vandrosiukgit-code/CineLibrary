import time

import pytest

from app.agents.movie_recommender import (
    MovieRecommender,
    MovieRecommenderOutputError,
)
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.schemas.movie_research import MovieLibrarianResult
from app.schemas.recommendations import RecommendationRequest
from app.services.taste_profile import TasteProfileBuilder
from app.services.recommendation_jobs import RecommendationJobManager


class FakeMovieRepository:
    def list_taste_tags(self):
        return [
            {"code": "strength:story", "sentiment": 1},
            {"code": "emotion:lingering", "sentiment": 1},
        ]

    def list_movies(self, **_filters):
        return [
            {
                "id": 1,
                "tmdb_id": 157336,
                "title": "Интерстеллар",
                "original_title": "Interstellar",
                "release_year": 2014,
                "genres": [
                    {"display_name": "фантастика"},
                    {"display_name": "драма"},
                ],
                "user_data": {
                    "watched": True,
                    "personal_rating": 5,
                    "comment": "Понравились идеи и масштаб.",
                    "in_wishlist": False,
                    "tags": ["Сюжет", "Оставил послевкусие"],
                    "tag_codes": ["strength:story", "emotion:lingering"],
                },
            },
            {
                "id": 2,
                "tmdb_id": 329865,
                "title": "Прибытие",
                "original_title": "Arrival",
                "release_year": 2016,
                "genres": [
                    {"display_name": "фантастика"},
                    {"display_name": "драма"},
                ],
                "user_data": {
                    "watched": True,
                    "personal_rating": 4,
                    "comment": "",
                    "in_wishlist": False,
                    "tags": ["Сюжет"],
                    "tag_codes": ["strength:story"],
                },
            },
        ]


def test_taste_profile_is_evidence_first_and_excludes_watched_movies():
    profile = TasteProfileBuilder(FakeMovieRepository()).build()

    assert profile["format"] == "cinelibrary.taste-profile.v1"
    assert profile["summary"]["watchedMovies"] == 2
    assert {movie["tmdbId"] for movie in profile["doNotRecommend"]} == {
        157336,
        329865,
    }
    story = next(
        signal
        for signal in profile["tagSignals"]
        if signal["code"] == "strength:story"
    )
    assert story["uses"] == 2
    assert story["averageRatingOutOf5"] == 4.5


class FakeBrain:
    def __init__(self, movies):
        self.movies = movies

    def generate_json(self, *_args, **_kwargs):
        return {"movies": self.movies}


class FakeLibrarian:
    def research_movie(self, movie_input):
        return MovieLibrarianResult(
            inputText=movie_input,
            status="failed",
            identification=None,
            movie=None,
            existingMovieId=None,
            sources=[],
            issues=["test result"],
        )

    def research_movies(self, movie_inputs):
        return [self.research_movie(movie_input) for movie_input in movie_inputs]


class FakeProfileBuilder:
    def build(self):
        return {
            "format": "cinelibrary.taste-profile.v1",
            "doNotRecommend": [{"tmdbId": 1, "title": "Просмотренный"}],
        }


class FakePeopleRepository:
    def find_by_tmdb_id(self, _tmdb_id):
        return None


class FakeTMDB:
    pass


def recommendation_request(count=2):
    return RecommendationRequest(
        count=count,
        answers=[
            {
                "cardId": "current-intent",
                "title": "Текущее желание",
                "values": ["Напряжённое интеллектуальное кино"],
                "skipped": False,
            }
        ],
    )


def test_recommender_builds_temporary_session_with_requested_count():
    sessions = RecommendationSessionStore()
    recommender = MovieRecommender(
        brain=FakeBrain(
            [
                {"title": "Фильм A", "releaseYear": 2020, "relevance": 91},
                {"title": "Фильм B", "releaseYear": 2021, "relevance": 84},
            ]
        ),
        tmdb=FakeTMDB(),
        librarian=FakeLibrarian(),
        profile_builder=FakeProfileBuilder(),
        people_repository=FakePeopleRepository(),
        sessions=sessions,
    )

    response = recommender.recommend(recommendation_request())

    assert len(response.movies) == 2
    assert response.movies[0].suggestion.relevance == 91
    assert sessions.get(response.session_id)["profile"]["doNotRecommend"]


def test_recommender_rejects_wrong_number_of_movies():
    recommender = MovieRecommender(
        brain=FakeBrain(
            [{"title": "Только один", "releaseYear": 2020, "relevance": 90}]
        ),
        tmdb=FakeTMDB(),
        librarian=FakeLibrarian(),
        profile_builder=FakeProfileBuilder(),
        people_repository=FakePeopleRepository(),
        sessions=RecommendationSessionStore(),
    )

    with pytest.raises(MovieRecommenderOutputError):
        recommender.recommend(recommendation_request(count=2))


def wait_for_terminal_job(manager, job_id):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job["status"] in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.01)
    raise AssertionError("Recommendation job did not finish")


def test_recommendation_job_records_progress():
    manager = RecommendationJobManager()

    def runner(progress, _cancelled):
        progress("Первый этап")
        progress("Второй этап")
        return None

    created = manager.start(runner)
    completed = wait_for_terminal_job(manager, created["job_id"])

    assert completed["status"] == "completed"
    assert [entry["message"] for entry in completed["logs"]][-3:] == [
        "Первый этап",
        "Второй этап",
        "Подбор завершён.",
    ]


def test_recommendation_job_can_be_cancelled():
    manager = RecommendationJobManager()

    def runner(_progress, cancelled):
        while not cancelled():
            time.sleep(0.01)
        return None

    created = manager.start(runner)
    manager.cancel(created["job_id"])
    cancelled = wait_for_terminal_job(manager, created["job_id"])

    assert cancelled["status"] == "cancelled"
    assert cancelled["logs"][-1]["message"] == "Подбор остановлен пользователем."
