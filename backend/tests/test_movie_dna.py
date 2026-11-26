from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.routes import movie_librarian
from app.main import create_app
from app.repositories.movie_dna import MovieDNARepository
from app.repositories.movielens import MovieLensIndex
from app.schemas.movie_research import MovieIdentification, MovieLibrarianResult
from app.services import movie_dna as movie_dna_service
from app.services.movie_dna import MovieDNAService


TARGET = 335984
ORIGINAL = 329865
BASE = "/api/agents/movie-librarian-1/movie-dna"
SEED = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"


def candidate(tmdb_id, title, original_title=None):
    return {
        "tmdbId": tmdb_id, "title": title, "originalTitle": original_title,
        "releaseYear": 2000,
    }


@pytest.fixture
def movie_dna(tmp_path, monkeypatch):
    (tmp_path / "links.csv").write_text(
        "movieId,imdbId,tmdbId\n1,1,101\n2,2,102\n3,3,103\n4,4,329865\n1,1,104\n",
        encoding="utf-8",
    )
    (tmp_path / "genome-tags.csv").write_text(
        "tagId,tag\n1,mood\n2,humor\n", encoding="utf-8"
    )
    (tmp_path / "genome-scores.csv").write_text(
        "movieId,tagId,relevance\n1,1,0.2\n1,2,0\n2,1,0.6\n3,1,0.8\n3,2,0.6\n4,1,0.9\n",
        encoding="utf-8",
    )
    index = MovieLensIndex(tmp_path / "movielens.db")
    index.import_csv(tmp_path, "demo")
    monkeypatch.setattr(movie_dna_service, "MovieLensIndex", lambda: index)
    brain = Mock()
    brain.generate_text.return_value = json.dumps({
        "target_tmdb_id": TARGET,
        "analogs": [
            {"title": title, "year": 2000}
            for title in ("Film A", " film   a ", "Film B", "Same Title", "Film C", "Film A Alias")
        ],
    })
    tmdb = Mock()
    search = {
        "Film A": [candidate(101, "Localized A", "Film A"), candidate(999, "Different")],
        "Film B": [candidate(102, "Film B")],
        "Same Title": [candidate(201, "Same Title"), candidate(202, "Same Title")],
        "Film C": [candidate(103, "Film C")],
        "Film A Alias": [candidate(104, "Film A Alias")],
    }
    tmdb.search_movie.side_effect = lambda title, year: search[title]
    make_brain = Mock(return_value=brain)
    monkeypatch.setattr(movie_librarian.ReplicateGeminiClient, "from_environment", make_brain)
    monkeypatch.setattr(movie_librarian.TMDBClient, "from_environment", lambda: tmdb)
    with TestClient(create_app(tmp_path / "catalog.db", seed_path=SEED)) as client:
        yield client, brain, tmdb, make_brain, index


def test_estimate_uses_confirmed_originals_and_reweights_missing_tags(movie_dna):
    client, brain, tmdb, _, _ = movie_dna
    card_before = client.get("/api/movies/1").json()
    assert client.get(f"{BASE}/{TARGET}").json()["status"] == "no_tmdb_mapping"

    response = client.post(f"{BASE}/{TARGET}/estimate")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "found"
    assert result["source"] == "estimated"
    assert result["dataset_version"] == "demo"
    assert result["algorithm_version"].startswith("reciprocal-rank-v1")
    assert result["evaluated_at"].endswith("+00:00")
    assert [donor["tmdb_id"] for donor in result["donors"]] == [101, 102, 103]
    assert [donor["rank"] for donor in result["donors"]] == [1, 3, 5]
    assert [donor["weight"] for donor in result["donors"]] == pytest.approx([15/23, 5/23, 3/23])
    assert result["selection_status"] == "complete"
    assert [analog["status"] for analog in result["analogs"]] == [
        "accepted", "duplicate_suggestion", "accepted", "tmdb_ambiguous",
        "accepted", "duplicate_genome",
    ]
    assert result["analogs"][3]["title"] == "Same Title"
    assert result["analogs"][5]["tmdb_id"] == 104
    mood, humor = result["tags"]
    assert mood["relevance"] == pytest.approx(8.4/23)
    assert humor["relevance"] == pytest.approx(0.1)
    assert humor["variance"] == pytest.approx(0.05)
    assert humor["donor_count"] == 2
    assert client.get(f"{BASE}/{TARGET}").json() == result
    assert client.post(f"{BASE}/{TARGET}/estimate").json() == result
    assert client.get("/api/movies/1").json() == card_before
    brain.generate_text.assert_called_once()
    assert brain.generate_text.call_args.kwargs == {
        "temperature": 0, "max_output_tokens": 4096, "thinking_level": "low",
    }
    model_data = brain.generate_text.call_args.args[1]
    assert set(model_data) == {"target_tmdb_id", "title", "original_title", "year", "genres", "overview"}
    assert tmdb.search_movie.call_count == 5


def test_original_and_unavailable_index_never_start_model(movie_dna):
    client, _, _, make_brain, index = movie_dna
    assert client.post(f"{BASE}/{ORIGINAL}/estimate").json()["source"] == "original"
    assert client.post(f"{BASE}/10000000/estimate").status_code == 404

    index.path.unlink()
    assert client.post(f"{BASE}/{TARGET}/estimate").json()["status"] == "index_unavailable"
    make_brain.assert_not_called()


def test_recommendation_sends_original_and_cached_dna_to_gemini(movie_dna, monkeypatch):
    client, brain, tmdb, _, _ = movie_dna
    assert client.post(f"{BASE}/{TARGET}/estimate").json()["source"] == "estimated"
    brain.reset_mock()
    tmdb.reset_mock()
    reason = "Ироничная история с выразительной атмосферой подходит под запрос на комедию."
    brain.generate_json.return_value = {"movies": [{
        "title": "Suggested title", "releaseYear": 2021, "relevance": 90, "reason": reason,
    }]}
    tmdb.get_movie_candidate.return_value = {
        "tmdbId": 438631, "title": "Dune", "originalTitle": "Dune", "releaseYear": 2021,
    }
    tmdb.get_movie_credits.return_value = {"cast": [], "crew": []}
    result = MovieLibrarianResult(
        inputText="Suggested title (2021)", status="already_exists",
        identification=MovieIdentification(
            inputText="Suggested title (2021)", status="identified", confidence=1, tmdbId=438631,
            originalTitle="Dune", releaseYear=2021, reason="test", candidates=[],
        ),
        movie=None, existingMovieId=3, sources=[], issues=[],
    )
    monkeypatch.setattr(movie_librarian.MovieLibrarian, "research_movies", Mock(return_value=[result]))
    answer = {
        "cardId": "current-intent", "title": "На сегодня", "values": ["Комедия"],
        "skipped": False,
    }
    genres = {
        "cardId": "genres", "title": "Жанры", "skipped": False,
        "values": ["Исключить: ужасы", "Желательно: детектив", "Желательно: приключения"],
    }

    response = client.post(
        "/api/agents/movie-recommender/recommend", json={
            "count": 1, "answers": [answer, genres],
            "references": [{"tmdbId": ORIGINAL, "relation": "similar"}],
        },
    )

    assert response.status_code == 200, response.text
    brain.generate_json.assert_called_once()
    brain.generate_text.assert_not_called()
    tmdb.search_movie.assert_not_called()
    instructions, payload = brain.generate_json.call_args.args
    assert "Current-request wishes and constraints take priority" in instructions
    assert payload["currentRequest"]["answers"] == [answer, genres]
    assert payload["referenceFeatures"] == {"1": "mood"}
    assert response.json()["movies"][0]["suggestion"]["reason"] == reason
    assert response.json()["movies"][0]["suggestion"]["title"] == "Dune"
    assert "Сходство с ориентирами недоступно" in response.json()["movies"][0]["scoreExplanation"]
    rows = response.json()["movies"][0]["breakdown"]["matches"]
    assert [row["label"] for row in rows if row["label"].startswith(("Желательно:", "Исключить:"))] == [
        "Желательно: приключения",
    ]
    profile = payload["tasteProfile"]
    assert profile == response.json()["tasteProfile"]
    signals = profile["movieDNASignals"]
    assert signals["ratedMoviesWithOriginal"] == signals["ratedMoviesWithEstimated"] == 1
    assert signals["associatedWithHigherRatings"][0] == {
        "name": "mood", "score": 2.165, "highRatedMovies": 2, "lowRatedMovies": 0,
    }
    excluded = client.post("/api/agents/movie-recommender/recommend", json={
        "count": 1, "answers": [{**genres, "values": ["Исключить: приключения"]}],
    })
    assert excluded.status_code == 200
    assert excluded.json()["movies"] == []


def test_original_takes_priority_when_index_later_contains_target(movie_dna):
    client, brain, _, _, index = movie_dna
    assert client.post(f"{BASE}/{TARGET}/estimate").json()["source"] == "estimated"
    with (index.path.parent / "links.csv").open("a", encoding="utf-8") as links_file:
        links_file.write("4,4,335984\n")
    index.import_csv(index.path.parent, "demo")

    result = client.post(f"{BASE}/{TARGET}/estimate").json()

    assert result["source"] == "original"
    assert result["tags"][0]["relevance"] == 0.9
    brain.generate_text.assert_called_once()


def test_insufficient_donors_are_cached_without_fabricating_tags(movie_dna):
    client, brain, tmdb, _, _ = movie_dna
    tmdb.search_movie.side_effect = lambda title, year: (
        [candidate(101, title)] if title == "Film A" else []
    )

    result = client.post(f"{BASE}/{TARGET}/estimate").json()

    assert result["status"] == "insufficient_analogs"
    assert result["source"] is None
    assert result["donor_count"] == 1
    assert result["tags"] == []
    assert result["analogs"][2]["status"] == "tmdb_not_found"
    assert client.post(f"{BASE}/{TARGET}/estimate").json() == result
    brain.generate_text.assert_called_once()


def test_invalid_model_result_releases_claim_and_allows_retry(movie_dna):
    client, brain, tmdb, _, _ = movie_dna
    valid = brain.generate_text.return_value
    wrong_target = json.dumps({**json.loads(valid), "target_tmdb_id": ORIGINAL})
    brain.generate_text.side_effect = [wrong_target, valid]

    assert client.post(f"{BASE}/{TARGET}/estimate").status_code == 502
    tmdb.search_movie.assert_not_called()
    assert client.get(f"{BASE}/{TARGET}").json()["status"] == "no_tmdb_mapping"
    assert client.post(f"{BASE}/{TARGET}/estimate").json()["source"] == "estimated"
    assert brain.generate_text.call_count == 2


def test_truncated_response_uses_complete_analogs_and_saves_their_statuses(movie_dna):
    client, brain, tmdb, _, _ = movie_dna
    titles = ["Clue", "Murder by Death", "The Last of Sheila", "Gosford Park"]
    brain.generate_text.return_value = """{
        "target_tmdb_id": 335984,
        "analogs": [
            {"title": "Clue", "year": 1985},
            {"title": "Murder by Death", "year": 1976},
            {"title": "The Last of Sheila", "year": 1973},
            {"title": "Gosford Park", "year": 2001},
            {
    """
    tmdb.search_movie.side_effect = lambda title, year: [
        {**candidate([101, 102, 103, ORIGINAL][titles.index(title)], title), "releaseYear": year},
    ]

    response = client.post(f"{BASE}/{TARGET}/estimate")

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == "estimated"
    assert result["selection_status"] == "partial"
    assert result["donor_count"] == 4
    assert [item["title"] for item in result["analogs"]] == titles
    assert all(item["status"] == "accepted" for item in result["analogs"])
    assert client.get(f"{BASE}/{TARGET}").json() == result
    brain.generate_text.assert_called_once()
    assert tmdb.search_movie.call_count == 4


@pytest.mark.parametrize("fragment", ['[{"title":', '[{"title": "A"}, broken'])
def test_unusable_model_output_returns_error_without_searching(movie_dna, fragment):
    client, brain, tmdb, _, _ = movie_dna
    brain.generate_text.return_value = f'{{"target_tmdb_id": {TARGET}, "analogs": {fragment}'

    assert client.post(f"{BASE}/{TARGET}/estimate").status_code == 502
    assert client.get(f"{BASE}/{TARGET}").json()["status"] == "no_tmdb_mapping"
    brain.generate_text.assert_called_once()
    tmdb.search_movie.assert_not_called()


def test_active_claim_blocks_second_estimate_and_expired_claim_can_be_replaced(movie_dna):
    client, _, _, make_brain, index = movie_dna
    repository = MovieDNARepository(client.app.state.movie_repository.database)
    version = MovieDNAService(index, repository).algorithm_version
    key = (TARGET, "demo", version)
    first = repository.claim(*key)
    assert first

    assert repository.claim(*key) is None
    assert client.post(f"{BASE}/{TARGET}/estimate").json()["status"] == "in_progress"
    make_brain.assert_not_called()

    with closing(repository.database.connect()) as connection, connection:
        connection.execute("UPDATE movie_dna_estimates SET claim_until = 0")
    second = repository.claim(*key)
    assert second and second != first
    repository.release(*key, first)
    assert repository.get(*key)["status"] == "in_progress"
import json
