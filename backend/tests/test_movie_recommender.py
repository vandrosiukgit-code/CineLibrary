import time
from unittest.mock import Mock, call

import pytest
from pydantic import ValidationError

from app.agents.movie_recommender import (
    MovieRecommender,
    MovieRecommenderOutputError,
)
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.schemas.movie_research import MovieIdentification, MovieLibrarianResult
from app.schemas.recommendations import GeminiRecommendationOutput, RecommendationRequest, SuggestedMovie
from app.services.recommendation_scoring import score_recommendation
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


def test_movie_dna_signals_combine_original_and_estimated_tags_with_ratings():
    movies = FakeMovieRepository().list_movies()
    for tmdb_id, rating in [(55, 2), (56, 5), (57, 3), (58, None), (None, 5)]:
        movies.append({
            **movies[0], "tmdb_id": tmdb_id,
            "user_data": {**movies[0]["user_data"], "personal_rating": rating},
        })
    repository = Mock(spec=FakeMovieRepository)
    repository.list_movies.return_value = movies
    repository.list_taste_tags.return_value = []
    dna = Mock()
    pace = {"tag_id": 1, "name": "slow paced", "relevance": 0.8}
    bleak = {"tag_id": 2, "name": "bleak", "relevance": 0.9}
    results = {
        157336: {"status": "found", "source": "original", "tags": [pace]},
        329865: {"status": "found", "source": "estimated", "tags": [pace]},
        55: {"status": "found", "source": "original", "tags": [pace, bleak]},
        56: {"status": "no_tmdb_mapping"},
        57: {"status": "found", "source": "original", "tags": [pace]},
        58: {"status": "found", "source": "estimated", "tags": [pace, bleak]},
    }
    dna.get.side_effect = results.__getitem__

    profile = TasteProfileBuilder(repository, movie_dna=dna).build()

    repository.list_movies.assert_called_once_with(watched=True, sort="release_desc")
    assert dna.get.call_args_list == [
        call(157336), call(329865), call(55), call(56), call(57), call(58),
    ]
    assert profile["movieDNASignals"] == {
        "ratedMoviesWithOriginal": 2,
        "ratedMoviesWithEstimated": 1,
        "associatedWithHigherRatings": [
            {"name": "slow paced", "movies": 5, "averageRelevance": 0.8, "score": 0.12,
             "weightedRelevance": 0.92, "highRatedMovies": 2, "lowRatedMovies": 1},
        ],
        "associatedWithLowerRatings": [
            {"name": "bleak", "movies": 2, "averageRelevance": 0.9, "score": -0.225,
             "weightedRelevance": 0.675, "highRatedMovies": 0, "lowRatedMovies": 1},
        ],
        "viewingContext": [
            {"name": "bleak", "movies": 2, "averageRelevance": 0.9},
            {"name": "slow paced", "movies": 5, "averageRelevance": 0.8},
        ],
    }


def test_same_watched_trait_is_lowered_by_low_ratings_and_raised_by_high_ratings():
    movie = FakeMovieRepository().list_movies()[0]
    repository = Mock(spec=FakeMovieRepository)
    repository.list_movies.return_value = [movie]
    repository.list_taste_tags.return_value = []
    dna = Mock()
    dna.get.return_value = {"status": "found", "source": "original", "tags": [
        {"tag_id": 1, "name": "pace", "relevance": 0.6},
    ]}
    builder = TasteProfileBuilder(repository, movie_dna=dna)

    weights = []
    for rating in [1, 2, 3, 4, 5, None]:
        movie["user_data"]["personal_rating"] = rating
        signals = builder.build()["movieDNASignals"]
        baseline = signals["viewingContext"][0]["averageRelevance"]
        assert baseline == 0.6
        adjustments = signals["associatedWithHigherRatings"] + signals["associatedWithLowerRatings"]
        weights.append(adjustments[0]["weightedRelevance"] if adjustments else baseline)

    assert weights == [0.0, 0.3, 0.6, 0.9, 1.2, 0.6]


def test_taste_profile_preserves_existing_signals_without_movie_dna():
    dna = Mock()
    dna.get.return_value = {"status": "index_unavailable"}
    profile = TasteProfileBuilder(FakeMovieRepository(), movie_dna=dna).build()

    assert "movieDNASignals" not in profile
    assert profile["summary"]["ratedMovies"] == 2
    assert profile["genreSignals"] and profile["tagSignals"] and profile["movieEvidence"]


class FakeBrain:
    def __init__(self, movies):
        self.movies = movies

    def generate_json(self, *_args, **_kwargs):
        return {"movies": self.movies}


class FakeLibrarian:
    def __init__(self, ids=None):
        self.ids = ids or {}

    def research_movie(self, movie_input):
        tmdb_id = self.ids.get(movie_input)
        identification = MovieIdentification(
            inputText=movie_input, status="identified", confidence=1, tmdbId=tmdb_id,
            originalTitle=movie_input, releaseYear=2020, reason="test", candidates=[],
        ) if tmdb_id is not None else None
        return MovieLibrarianResult(
            inputText=movie_input,
            status="already_exists" if identification else "failed",
            identification=identification,
            movie=None,
            existingMovieId=tmdb_id,
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
    def get_movie_candidate(self, tmdb_id, *, language):
        assert language == "en-US"
        return {
            "tmdbId": tmdb_id, "title": f"International title {tmdb_id}",
            "originalTitle": "Original title", "releaseYear": 2020,
        }

    def get_movie_credits(self, _tmdb_id):
        return {"cast": [], "crew": []}


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
    reasons = [
        "Камерный детектив подходит под ваше желание посмотреть напряжённое кино.",
        "Нелинейный сюжет предлагает загадку, над которой интересно подумать.",
    ]
    recommender = MovieRecommender(
        brain=FakeBrain(
            [
                {"title": "Фильм A", "releaseYear": 2020, "relevance": 91, "reason": reasons[0]},
                {"title": "Фильм B", "releaseYear": 2021, "relevance": 84, "reason": reasons[1]},
            ]
        ),
        tmdb=FakeTMDB(),
        librarian=FakeLibrarian({"Фильм A (2020)": 2, "Фильм B (2021)": 3}),
        profile_builder=FakeProfileBuilder(),
        people_repository=FakePeopleRepository(),
        sessions=sessions,
    )

    response = recommender.recommend(recommendation_request())

    assert len(response.movies) == 2
    assert response.movies[0].suggestion.relevance == 91
    assert [movie.suggestion.reason for movie in response.movies] == reasons
    assert sessions.get(response.session_id)["profile"]["doNotRecommend"]


def test_recommender_excludes_watched_alias_duplicate_id_and_unidentified_title():
    titles = ["Watched under another name", "First candidate", "Candidate alias", "Unknown"]
    tmdb = Mock(wraps=FakeTMDB())
    sessions = RecommendationSessionStore()
    recommender = MovieRecommender(
        brain=FakeBrain([
            {"title": title, "releaseYear": 2020, "relevance": 90, "reason": "Камерный детектив."}
            for title in titles
        ]),
        tmdb=tmdb,
        librarian=FakeLibrarian({f"{title} (2020)": tmdb_id for title, tmdb_id in zip(titles, [1, 2, 2])}),
        profile_builder=FakeProfileBuilder(),
        people_repository=FakePeopleRepository(),
        sessions=sessions,
    )

    response = recommender.recommend(recommendation_request(count=len(titles)))

    assert [movie.suggestion.title for movie in response.movies] == ["International title 2"]
    assert list(sessions.get(response.session_id)["recommendations"]) == [response.movies[0].id]
    tmdb.get_movie_candidate.assert_called_once_with(2, language="en-US")
    tmdb.get_movie_credits.assert_called_once_with(2)


def test_recommender_reranks_with_average_reference_dna_and_explains_real_matches():
    titles = ["High wish score", "High reference score", "DNA unavailable"]
    brain = Mock()
    brain.generate_json.return_value = {
        "movies": [
            {"title": title, "releaseYear": 2020, "relevance": value, "reason": "Подходит для вечера.",
             "wishMatches": {"0-0": [{"label": "Оценка", "score": value, "detail": "Совпадение."}]}}
            for title, value in zip(titles, [95, 80, 99], strict=True)
        ],
        "featureLabels": {"11": "сухой юмор", "99": "несуществующий признак"},
    }
    relevance_by_id = {101: 1.0, 102: 0.6, 2: 0.2, 3: 0.8}
    dna = Mock()
    dna.get.side_effect = lambda tmdb_id: (
        {"status": "found", "tags": [
            {"tag_id": 11, "name": "dry humor", "relevance": relevance_by_id[tmdb_id]}
        ]} if tmdb_id in relevance_by_id else {"status": "no_original_genome"}
    )
    recommender = MovieRecommender(
        brain=brain, tmdb=FakeTMDB(),
        librarian=FakeLibrarian({f"{title} (2020)": tmdb_id for tmdb_id, title in enumerate(titles, 2)}),
        profile_builder=FakeProfileBuilder(), people_repository=FakePeopleRepository(),
        sessions=RecommendationSessionStore(), movie_dna=dna,
    )
    request = recommendation_request(count=3).model_dump(by_alias=True)
    request["references"] = [
        {"tmdbId": tmdb_id, "relation": "similar"} for tmdb_id in (101, 102, 101)
    ]

    response = recommender.recommend(RecommendationRequest.model_validate(request))

    assert [movie.existing_movie_id for movie in response.movies] == [3, 2, 4]
    assert [movie.suggestion.relevance for movie in response.movies] == [88, 67, 99]
    best = response.movies[0].score_explanation
    assert "Сходство с ориентирами — 100 из 100" in best
    assert "По пожеланиям — 80 из 100" in best
    assert "сухой юмор" in best and "несуществующий признак" not in best
    assert response.movies[0].breakdown.matches[0].score == 80
    assert response.movies[0].breakdown.matches[1].detail == "Главные совпадения — сухой юмор."
    assert "Сходство с ориентирами недоступно" in response.movies[2].score_explanation
    assert response.movies[2].breakdown.chef_pick
    assert response.movies[2].breakdown.reference_score is None
    assert "Сходство с ориентирами — 25 из 100" in response.movies[1].score_explanation
    brain.generate_json.assert_called_once()
    assert brain.generate_json.call_args.args[1]["referenceFeatures"] == {"11": "dry humor"}
    assert brain.generate_json.call_args.args[1]["requestMovieDNA"] == {
        "seek": [{"feature": "dry humor", "weight": 0.8}], "avoid": [],
    }
    dna.estimate.assert_not_called()


def test_avoid_reference_lowers_score_without_a_wish_score():
    suggestion = SuggestedMovie(title="Фильм", relevance=95, reason="Подходит для вечера.")
    score, explanation, breakdown = score_recommendation(
        suggestion, {"avoid": {11: ("dry humor", 0.8)}}, {11: 0.6}, {11: "сухой юмор"},
        has_wishes=False, has_references=True,
    )

    assert score == 25
    assert breakdown.matches[0].score == 25
    assert "сухой юмор" in explanation
    assert "95" not in explanation


def test_recommender_rejects_wrong_number_of_movies():
    recommender = MovieRecommender(
        brain=FakeBrain(
            [{
                "title": "Только один", "releaseYear": 2020, "relevance": 90,
                "reason": "Расследование подходит под ваш запрос на напряжённое кино.",
            }]
        ),
        tmdb=FakeTMDB(),
        librarian=FakeLibrarian(),
        profile_builder=FakeProfileBuilder(),
        people_repository=FakePeopleRepository(),
        sessions=RecommendationSessionStore(),
    )

    with pytest.raises(MovieRecommenderOutputError, match="expected 2"):
        recommender.recommend(recommendation_request(count=2))


@pytest.mark.parametrize("reason", [{}, {"reason": "  "}, {"reason": "а" * 241}])
def test_recommendation_requires_short_non_empty_reason(reason):
    with pytest.raises(ValidationError) as error:
        GeminiRecommendationOutput.model_validate(
            {"movies": [{"title": "Фильм", "relevance": 90, **reason}]}
        )

    assert error.value.errors()[0]["loc"] == ("movies", 0, "reason")


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
