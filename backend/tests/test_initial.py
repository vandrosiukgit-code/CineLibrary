from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.main import create_app


DEMO_SEED = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "movies-test.db", seed_path=DEMO_SEED)
    with TestClient(app) as test_client:
        yield test_client


def test_new_database_starts_without_demo_movies(tmp_path):
    app = create_app(tmp_path / "movies-empty.db")
    with TestClient(app) as test_client:
        response = test_client.get("/api/movies")

    assert response.status_code == 200
    assert response.json() == []


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
        "tagCodes": [],
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


def test_availability_filter_uses_same_status_as_catalog_card(client):
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute("INSERT INTO movie_files (movie_id, status) VALUES (3, 'available')")
        connection.execute("DELETE FROM movie_files WHERE movie_id = 4")

    for status in ("available", "downloading", "missing"):
        response = client.get("/api/movies", params={"availability": status, "inWishlist": "true"})
        assert response.status_code == 200
        assert [movie["id"] for movie in response.json()] == {"available": [3], "downloading": [], "missing": [4]}[status]


def test_genre_filter_options_come_from_watched_catalog(client):
    response = client.get("/api/movies/genres", params={"watched": "true"})

    assert response.status_code == 200
    genres = response.json()
    watched_movies = client.get("/api/movies", params={"watched": "true"}).json()
    expected = {
        genre["displayName"]
        for movie in watched_movies
        for genre in movie["genres"]
    }
    assert set(genres) == expected
    assert len(genres) == len(set(genres))


def test_search_uses_display_and_original_titles(client):
    assert [
        movie["originalTitle"]
        for movie in client.get("/api/movies", params={"search": "Arrival"}).json()
    ] == ["Arrival"]
    assert [
        movie["originalTitle"]
        for movie in client.get("/api/movies", params={"search": "Интер"}).json()
    ] == ["Interstellar"]
    assert [
        movie["originalTitle"]
        for movie in client.get("/api/movies", params={"search": "интер"}).json()
    ] == ["Interstellar"]


def test_catalog_navigation_filters_search_people_and_sort(client):
    by_person = client.get("/api/movies", params={"search": "Villeneuve"})
    assert by_person.status_code == 200
    assert [movie["originalTitle"] for movie in by_person.json()] == [
        "Dune",
        "Blade Runner 2049",
        "Arrival",
    ]

    high_rated = client.get(
        "/api/movies",
        params={"personalRatingMin": 5, "sort": "title_asc"},
    )
    assert high_rated.status_code == 200
    assert all(
        movie["userData"]["personalRating"] == 5
        for movie in high_rated.json()
    )

    without_rating = client.get(
        "/api/movies", params={"hasPersonalRating": "false"}
    )
    assert without_rating.status_code == 200
    assert all(
        movie["userData"]["personalRating"] is None
        for movie in without_rating.json()
    )


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


def test_structured_taste_tags_can_be_added_and_replaced(client):
    definitions = client.get("/api/movies/taste-tags")
    assert definitions.status_code == 200
    assert {tag["category"] for tag in definitions.json()} == {
        "viewing",
        "emotion",
        "strength",
        "weakness",
        "outcome",
    }

    first = client.patch(
        "/api/movies/1/user-data",
        json={"tagCodes": ["viewing:captivating", "strength:acting"]},
    )
    assert first.status_code == 200
    assert first.json()["userData"]["tagCodes"] == [
        "strength:acting",
        "viewing:captivating",
    ]

    second = client.patch(
        "/api/movies/1/user-data",
        json={"tagCodes": ["outcome:rewatch"]},
    )
    assert second.status_code == 200
    assert second.json()["userData"]["tagCodes"] == ["outcome:rewatch"]
    assert "Хочу пересмотреть" in second.json()["userData"]["tags"]
    assert "Хорошая атмосфера" in second.json()["userData"]["tags"]


def test_download_request_is_saved_without_starting_download(client):
    movie = client.get("/api/movies/1").json()
    response = client.post(
        "/api/movies/download-requests",
        json={
            "tmdbMovieId": movie["tmdbId"],
            "localMovieId": movie["id"],
            "title": movie["title"],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "requested"
    assert client.get("/api/movies/1").json()["availability"] == "available"
    requests = client.get("/api/movies/download-requests").json()
    assert requests[0]["tmdbMovieId"] == movie["tmdbId"]
