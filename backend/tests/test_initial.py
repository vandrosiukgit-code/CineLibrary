from fastapi.testclient import TestClient
import pytest

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "movies-test.db")
    with TestClient(app) as test_client:
        yield test_client


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["application"] == "CineLibrary"


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_seed_contains_five_movies_and_preserves_personal_state(client):
    response = client.get("/api/movies")

    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 5

    by_title = {movie["originalTitle"]: movie for movie in movies}
    assert by_title["Blade Runner 2049"]["userData"] == {
        "watched": True,
        "personalRating": 5,
        "comment": "",
        "inWishlist": False,
        "tags": ["Хорошая атмосфера", "Оригинальная идея"],
    }
    assert by_title["Dune"]["availability"] == "downloading"
    assert by_title["Dune"]["userData"]["inWishlist"] is True
    assert by_title["Ex Machina"]["availability"] == "missing"


def test_filters_can_be_combined(client):
    response = client.get(
        "/api/movies",
        params={"watched": "false", "inWishlist": "true"},
    )

    assert response.status_code == 200
    assert {movie["originalTitle"] for movie in response.json()} == {
        "Dune",
        "Ex Machina",
    }


def test_search_uses_display_and_original_titles(client):
    assert [
        movie["originalTitle"]
        for movie in client.get("/api/movies", params={"search": "Arrival"}).json()
    ] == ["Arrival"]
    assert [
        movie["originalTitle"]
        for movie in client.get("/api/movies", params={"search": "Интер"}).json()
    ] == ["Interstellar"]


def test_personal_data_can_be_updated_without_changing_metadata(client):
    original = client.get("/api/movies/3").json()

    response = client.patch(
        "/api/movies/3/user-data",
        json={"watched": True, "personalRating": 4, "inWishlist": False},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["originalTitle"] == original["originalTitle"]
    assert updated["tmdbId"] == original["tmdbId"]
    assert updated["userData"]["watched"] is True
    assert updated["userData"]["personalRating"] == 4
    assert updated["userData"]["inWishlist"] is False


def test_unknown_movie_returns_not_found(client):
    assert client.get("/api/movies/999").status_code == 404
    assert client.patch(
        "/api/movies/999/user-data", json={"watched": True}
    ).status_code == 404
