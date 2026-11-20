import pytest
from fastapi.testclient import TestClient

from app.agents.movie_librarian import MovieLibrarian, MovieLibrarianOutputError
from app.main import create_app


def identified_command(movie_input="Drive My Car"):
    return {
        "action": "submit_movie_identification",
        "arguments": {
            "inputText": movie_input,
            "status": "identified",
            "confidence": 0.98,
            "tmdbId": 758866,
            "originalTitle": "ドライブ・マイ・カー",
            "releaseYear": 2021,
            "reason": "TMDB candidate matches the translated title and year.",
            "candidates": [],
        },
    }


class FakeBrain:
    def __init__(self, movie_input="Drive My Car"):
        self.messages = [
            {
                "action": "search_tmdb_movie",
                "arguments": {"query": movie_input, "year": None},
            },
            identified_command(movie_input),
        ]
        self.calls = []

    def next_action(self, system_instruction, movie_input, history):
        self.calls.append((system_instruction, movie_input, history))
        return self.messages.pop(0)


class FakeTMDB:
    def __init__(self):
        self.bundle_calls = []

    def search_movie(self, query, year=None):
        return [
            {
                "tmdbId": 758866,
                "title": "Сядь за руль моей машины",
                "originalTitle": "ドライブ・マイ・カー",
                "originalLanguage": "ja",
                "releaseYear": 2021,
                "overview": "Описание",
            }
        ]

    def get_movie_candidate(self, tmdb_id):
        return self.search_movie("Drive My Car")[0]

    def get_movie_bundle(self, tmdb_id):
        self.bundle_calls.append(tmdb_id)
        cast = [
            {
                "name": f"Actor {index}",
                "original_name": f"俳優 {index}",
                "order": index,
            }
            for index in range(12)
        ]
        return {
            "localized": {
                "id": 758866,
                "title": "Сядь за руль моей машины",
                "original_title": "ドライブ・マイ・カー",
                "original_language": "ja",
                "release_date": "2021-08-18",
                "runtime": 179,
                "overview": "Режиссёр переживает потерю жены.",
                "poster_path": "/poster.jpg",
                "vote_average": 7.4,
                "genres": [{"id": 18, "name": "Драма"}],
                "production_companies": [{"name": "Bitters End"}],
                "external_ids": {"imdb_id": "tt14039582"},
                "release_dates": {
                    "results": [
                        {"iso_3166_1": "UA", "release_dates": []},
                        {
                            "iso_3166_1": "US",
                            "release_dates": [{"certification": "NR"}],
                        },
                    ]
                },
                "credits": {
                    "cast": cast,
                    "crew": [
                        {"name": "Ryusuke Hamaguchi", "job": "Director"},
                        {"name": "Teruhisa Yamamoto", "job": "Producer"},
                        {"name": "Executive", "job": "Executive Producer"},
                        {"name": "Ryusuke Hamaguchi", "job": "Screenplay"},
                        {"name": "Eiko Ishibashi", "job": "Original Music Composer"},
                        {"name": "Hidetoshi Shinomiya", "job": "Director of Photography"},
                    ],
                },
            },
            "english": {
                "title": "Drive My Car",
                "original_title": "ドライブ・マイ・カー",
                "release_date": "2021-08-18",
                "runtime": 179,
                "overview": "English overview",
                "poster_path": "/poster.jpg",
                "genres": [{"id": 18, "name": "Drama"}],
                "production_countries": [{"name": "Japan"}],
            },
        }


class FakeRepository:
    def __init__(self, existing=None):
        self.existing = existing
        self.lookups = []

    def find_by_tmdb_id(self, tmdb_id):
        self.lookups.append(tmdb_id)
        return self.existing


def test_brain_identifies_and_python_builds_card_from_tmdb():
    tmdb = FakeTMDB()
    librarian = MovieLibrarian(FakeBrain(), tmdb, FakeRepository())

    result = librarian.research_movie("Drive My Car")

    assert result.status == "draft_ready"
    assert result.movie.original_title == "ドライブ・マイ・カー"
    assert result.movie.title == "Сядь за руль моей машины"
    assert result.movie.tmdb_rating == 7.4
    assert result.movie.imdb_rating is None
    assert result.movie.certification.country == "US"
    assert len([c for c in result.movie.credits if c.credit_type == "actor"]) == 10
    assert {c.credit_type for c in result.movie.credits} == {
        "actor",
        "director",
        "producer",
        "writer",
        "composer",
    }
    assert all(c.person_id is None for c in result.movie.credits)
    assert all(c.display_name == c.canonical_name for c in result.movie.credits)
    assert result.movie.credits[0].canonical_name == "Actor 0"
    assert tmdb.bundle_calls == [758866]


def test_existing_tmdb_movie_is_not_downloaded_again():
    tmdb = FakeTMDB()
    repository = FakeRepository(existing={"id": 42})
    librarian = MovieLibrarian(FakeBrain(), tmdb, repository)

    result = librarian.research_movie("Drive My Car")

    assert result.status == "already_exists"
    assert result.existing_movie_id == 42
    assert result.movie is None
    assert tmdb.bundle_calls == []


def test_brain_cannot_select_unobserved_tmdb_id():
    brain = FakeBrain()
    brain.messages[1] = identified_command()
    brain.messages[1]["arguments"] = {
            "inputText": "Drive My Car",
            "status": "identified",
            "confidence": 0.99,
            "tmdbId": 999999,
            "originalTitle": "Invented",
            "releaseYear": 2021,
            "reason": "Invented ID",
            "candidates": [],
        }
    librarian = MovieLibrarian(brain, FakeTMDB(), FakeRepository())

    with pytest.raises(MovieLibrarianOutputError):
        librarian.identify("Drive My Car")


def test_batch_failure_does_not_stop_other_movies():
    class FailingThenWorkingBrain(FakeBrain):
        def __init__(self):
            super().__init__()
            self.first = True

        def next_action(self, system_instruction, movie_input, history):
            if self.first:
                self.first = False
                return {"action": "invalid", "arguments": {}}
            return super().next_action(system_instruction, movie_input, history)

    librarian = MovieLibrarian(
        FailingThenWorkingBrain(), FakeTMDB(), FakeRepository()
    )
    results = librarian.research_movies(["Broken", "Drive My Car"])

    assert results[0].status == "failed"
    assert results[1].status == "draft_ready"


def test_research_endpoint_uses_gemini_and_tmdb_tools(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.api.routes.movie_librarian.ReplicateGeminiClient.from_environment",
        lambda: FakeBrain(),
    )
    monkeypatch.setattr(
        "app.api.routes.movie_librarian.TMDBClient.from_environment",
        lambda: FakeTMDB(),
    )
    app = create_app(tmp_path / "movies-test.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/agents/movie-librarian-1/research",
            json={"movies": ["Drive My Car"]},
        )
        assert response.status_code == 200
        result = response.json()["results"][0]
        assert result["status"] == "draft_ready"
        assert result["movie"]["originalTitle"] == "ドライブ・マイ・カー"

        import_response = client.post(
            "/api/movies/import",
            json={
                "movie": result["movie"],
                "sources": result["sources"],
                "watched": True,
                "availability": "missing",
            },
        )
        assert import_response.status_code == 201
        imported = import_response.json()
        assert imported["tmdbId"] == 758866
        assert imported["tmdbRating"] == 7.4
        assert imported["imdbRating"] is None
        assert imported["userData"]["watched"] is True
        assert len(client.get("/api/movies").json()) == 1


def test_research_endpoint_requires_both_api_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    monkeypatch.delenv("TMDB_READ_ACCESS_TOKEN", raising=False)
    app = create_app(tmp_path / "movies-test.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/agents/movie-librarian-1/research",
            json={"movies": ["Arrival"]},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "REPLICATE_API_TOKEN is not configured"
