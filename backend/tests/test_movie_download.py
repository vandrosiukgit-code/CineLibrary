import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.clients.tmdb import TMDBClient
from app.main import create_app
from app.repositories.recommendation_sessions import RecommendationSessionNotFoundError
from app.services.telegram_delivery import TelegramDeliveryService
from tests.test_movie_librarian import FakeTMDB


REQUESTS = "/api/movies/download-requests"
SEED = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"
TELEGRAM_SUCCESS = {"ok": True, "result": {"message_id": 101}}
TELEGRAM_REFUSAL = {"ok": False, "description": "Demo delivery refused"}


def recommendation_session(client, movie_ids):
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute("UPDATE movie_files SET status = 'missing'")
    return client.app.state.recommendation_sessions.create(
        profile={}, prompt="", recommendations=[
            {"id": str(movie_id), "librarian_result": SimpleNamespace(
                status="already_exists", existing_movie_id=movie_id,
            )} for movie_id in movie_ids
        ],
    )


@pytest.fixture
def download_client(tmp_path, monkeypatch):
    tmdb = Mock(spec=TMDBClient)
    tmdb.get_movie_bundle.side_effect = FakeTMDB().get_movie_bundle
    tmdb.get_movie_credits.return_value = {"cast": [], "crew": []}
    telegram = Mock()
    monkeypatch.setattr(TMDBClient, "from_environment", lambda: tmdb)
    monkeypatch.setattr(TelegramDeliveryService, "_call", telegram)
    app = create_app(tmp_path / "movies-test.db", seed_path=SEED)
    with TestClient(app) as client:
        app.state.telegram_delivery.save_settings("demo-token", "demo-chat")
        yield client, telegram


def test_successful_download_request_preserves_existing_movie_state(download_client):
    client, telegram = download_client
    telegram.side_effect = [
        {"ok": True, "result": [{"message_id": 101}] * 3},
        {"ok": True, "result": {"message_id": 102}},
    ]
    before = {movie_id: client.get(f"/api/movies/{movie_id}").json() for movie_id in (1, 3, 4)}

    response = client.post(
        f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [335984, 438631, 264660]}
    )

    assert response.status_code == 201
    for result in response.json():
        movie_id = result["movie"]["id"]
        assert client.get(f"/api/movies/{movie_id}").json() == before[movie_id]
        assert result["downloadRequest"]["telegramMessageId"] == 101
    assert len(client.get(REQUESTS).json()) == 3
    album, text = telegram.call_args_list
    assert album.args[1] == "sendMediaGroup"
    assert text.args[1] == "sendMessage"
    media = json.loads(album.args[2]["media"])
    assert "CL-000001_Blade_Runner_2049" in media[0]["caption"]


def test_recommendation_download_refusal_and_retry_with_poster(download_client):
    client, telegram = download_client
    session = recommendation_session(client, [3])
    url = f"/api/agents/movie-recommender/sessions/{session}/promote-many"
    payload = {"recommendationIds": ["3"]}
    before = client.get("/api/movies/3").json()

    telegram.return_value = TELEGRAM_REFUSAL
    assert client.post(url, json=payload).status_code == 502
    assert client.get(REQUESTS).json() == []

    telegram.reset_mock()
    telegram.return_value = TELEGRAM_SUCCESS
    assert client.post(url, json=payload).status_code == 200
    telegram.assert_called_once()
    assert telegram.call_args.args[1] == "sendPhoto"
    assert client.get("/api/movies/3").json() == before


@pytest.mark.parametrize("size", [1, 5])
def test_download_by_tmdb_from_previous_results_after_restart(download_client, size):
    client, telegram = download_client
    session = recommendation_session(client, range(1, size + 1))
    tmdb_ids = [client.get(f"/api/movies/{index}").json()["tmdbId"] for index in range(1, size + 1)]
    database_path = client.app.state.movie_repository.database.path
    with TestClient(create_app(database_path)) as restarted:
        with pytest.raises(RecommendationSessionNotFoundError):
            restarted.app.state.recommendation_sessions.get(session)
        rejected = restarted.post(f"{REQUESTS}/by-tmdb", json={
            "tmdbMovieIds": [1, 2, 3, 4, 5, 6], "preferPosters": True,
        })
        assert rejected.status_code == 422
        telegram.assert_not_called()
        if size == 1:
            telegram.return_value = TELEGRAM_SUCCESS
        else:
            telegram.side_effect = [
                {"ok": True, "result": [{"message_id": index} for index in range(10, 15)]},
                TELEGRAM_SUCCESS,
            ]

        response = restarted.post(f"{REQUESTS}/by-tmdb", json={
            "tmdbMovieIds": tmdb_ids, "preferPosters": True,
        })

    assert response.status_code == 201, response.text
    assert [item["downloadRequest"]["tmdbMovieId"] for item in response.json()] == tmdb_ids
    if size == 1:
        assert telegram.call_args_list[0].args[1] == "sendPhoto"
    else:
        album, text = telegram.call_args_list
        assert album.args[1] == "sendMediaGroup"
        assert len(json.loads(album.args[2]["media"])) == 5
        assert text.args[1] == "sendMessage"


def test_recommendation_download_sends_five_posters_and_rejects_six(download_client):
    client, telegram = download_client
    session = recommendation_session(client, [1, 2, 3, 4, 5])
    url = f"/api/agents/movie-recommender/sessions/{session}/promote-many"
    ids = [str(movie_id) for movie_id in range(1, 6)]
    assert client.post(url, json={"recommendationIds": ids + ["6"]}).status_code == 422
    telegram.assert_not_called()
    telegram.side_effect = [
        {"ok": True, "result": [{"message_id": number} for number in range(10, 15)]},
        TELEGRAM_SUCCESS,
    ]

    result = client.post(url, json={"recommendationIds": ids})

    assert result.status_code == 200
    assert len(result.json()["results"]) == 5
    album, text = telegram.call_args_list
    assert album.args[1] == "sendMediaGroup"
    assert len(json.loads(album.args[2]["media"])) == 5
    assert text.args[1] == "sendMessage"


def test_recommendation_download_reports_confirmed_ids_on_partial_failure(download_client):
    client, telegram = download_client
    session = recommendation_session(client, [1, 2, 3])
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute("UPDATE movies SET poster_url = NULL WHERE id = 3")
    telegram.side_effect = [
        {"ok": True, "result": [{"message_id": 10}, {"message_id": 11}]},
        TELEGRAM_REFUSAL,
        TELEGRAM_SUCCESS,
    ]
    url = f"/api/agents/movie-recommender/sessions/{session}/promote-many"

    failed = client.post(url, json={"recommendationIds": ["1", "2", "3"]})

    assert failed.status_code == 502
    assert failed.json()["detail"]["deliveredTmdbIds"] == [335984, 329865]
    assert client.post(url, json={"recommendationIds": ["3"]}).status_code == 200
    assert len(client.get(REQUESTS).json()) == 3


@pytest.mark.parametrize("size", [2, 3, 4, 5])
def test_album_has_one_numbered_poster_and_receipt_per_film(download_client, size):
    client, telegram = download_client
    tmdb_ids = [335984, 329865, 438631, 264660, 157336][:size]
    message_ids = list(range(101, 101 + size))
    telegram.side_effect = [
        {"ok": True, "result": [{"message_id": value} for value in message_ids]},
        {"ok": True, "result": {"message_id": 200}},
    ]

    response = client.post(f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": tmdb_ids})

    assert response.status_code == 201
    album, text = telegram.call_args_list
    assert album.args[1] == "sendMediaGroup"
    assert text.args[1] == "sendMessage"
    media = json.loads(album.args[2]["media"])
    assert len(media) == size
    for index, photo in enumerate(media, 1):
        assert photo["media"].startswith("https://image.tmdb.org/")
        assert f"<b>{index}. " in photo["caption"]
        assert f"CL-{index:06d}_" in photo["caption"]
        assert f"/movie/{tmdb_ids[index - 1]}" in photo["caption"]
        assert f"CL-{index:06d}_" in text.args[2]["text"]
        assert f"/movie/{tmdb_ids[index - 1]}" in text.args[2]["text"]
    assert [row["downloadRequest"]["telegramMessageId"] for row in response.json()] == message_ids


@pytest.mark.parametrize("posters", [1, 2])
def test_group_uses_text_for_missing_posters_and_preserves_response_order(
    download_client, posters
):
    client, telegram = download_client
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute("UPDATE movies SET poster_url = NULL WHERE id = 1")
        if posters == 1:
            connection.execute("UPDATE movies SET poster_url = NULL WHERE id = 3")
    photo_reply = TELEGRAM_SUCCESS if posters == 1 else {
        "ok": True, "result": [{"message_id": 101}, {"message_id": 101}],
    }
    telegram.side_effect = [photo_reply, {"ok": True, "result": {"message_id": 102}}]

    response = client.post(
        f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [335984, 329865, 438631]}
    )

    assert response.status_code == 201
    photo, text = telegram.call_args_list
    assert photo.args[1] == ("sendPhoto" if posters == 1 else "sendMediaGroup")
    assert text.args[1] == "sendMessage"
    assert "CL-000001_" in text.args[2]["text"]
    assert ("CL-000002_" in text.args[2]["text"]) == (posters == 2)
    expected = [102, 101, 102 if posters == 1 else 101]
    assert [row["downloadRequest"]["telegramMessageId"] for row in response.json()] == expected


def test_rejected_album_retries_posters_individually(download_client):
    client, telegram = download_client
    telegram.side_effect = [TELEGRAM_REFUSAL, TELEGRAM_SUCCESS, TELEGRAM_REFUSAL, TELEGRAM_SUCCESS]

    response = client.post(f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [335984, 329865]})

    assert response.status_code == 201
    assert [call.args[1] for call in telegram.call_args_list] == [
        "sendMediaGroup", "sendPhoto", "sendPhoto", "sendMessage",
    ]
    assert "CL-000002_" in telegram.call_args.args[2]["text"]


def test_telegram_refusal_returns_502_and_preserves_existing_movie_state(download_client):
    client, telegram = download_client
    telegram.return_value = TELEGRAM_REFUSAL
    client.patch("/api/movies/4/user-data", json={"inWishlist": False}).raise_for_status()
    before = client.get("/api/movies/4").json()
    assert before["availability"] == "missing"

    response = client.post(f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [264660]})

    assert response.status_code == 502
    assert response.json() == {"detail": "Demo delivery refused"}
    assert client.get("/api/movies/4").json() == before
    assert client.get(REQUESTS).json() == []
    assert [call.args[1] for call in telegram.call_args_list] == ["sendPhoto", "sendMessage"]


def test_retry_after_telegram_refusal_reuses_new_movie_and_cl_id(download_client):
    client, telegram = download_client
    telegram.side_effect = [TELEGRAM_REFUSAL, TELEGRAM_REFUSAL, TELEGRAM_SUCCESS]
    payload = {"tmdbMovieIds": [758866]}

    assert client.post(f"{REQUESTS}/by-tmdb", json=payload).status_code == 502
    assert client.get(REQUESTS).json() == []
    [before] = client.get("/api/movies", params={"search": "Сядь за руль"}).json()
    assert before["availability"] == "missing"
    assert before["userData"]["inWishlist"] is False
    assert before["userData"]["watched"] is False

    response = client.post(f"{REQUESTS}/by-tmdb", json=payload)

    assert response.status_code == 201
    [result] = response.json()
    assert result["movie"] == before
    [request] = client.get(REQUESTS).json()
    assert request["localMovieId"] == before["id"]
    assert request["telegramMessageId"] == 101
    first_photo, fallback, second_photo = telegram.call_args_list
    assert first_photo.args[2] == second_photo.args[2]
    assert request["fileName"] in fallback.args[2]["text"]
    assert request["fileName"] in second_photo.args[2]["caption"]
    assert "Страны: Japan" in second_photo.args[2]["caption"]


def test_photo_refusal_falls_back_to_escaped_text(download_client):
    client, telegram = download_client
    telegram.side_effect = [TELEGRAM_REFUSAL, TELEGRAM_SUCCESS]
    database = client.app.state.movie_repository.database
    with database.connect() as connection:
        connection.execute(
            "UPDATE movies SET title = ?, imdb_rating = NULL, tmdb_rating = 0 WHERE id = 1",
            ("Название & <фильм>",),
        )

    response = client.post(f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [335984]})

    assert response.status_code == 201
    photo, fallback = telegram.call_args_list
    assert photo.args[1] == "sendPhoto"
    assert fallback.args[1] == "sendMessage"
    text = fallback.args[2]["text"]
    assert text == photo.args[2]["caption"]
    assert "Название &amp; &lt;фильм&gt; (2017)" in text
    assert "Blade Runner 2049" in text
    assert "IMDb: " not in text and "TMDB: " not in text
    assert "https://www.imdb.com/title/tt1856101/" in text


@pytest.mark.parametrize("has_poster", [True, False])
def test_long_single_request_uses_text_and_links_poster_when_available(
    download_client, has_poster
):
    client, telegram = download_client
    telegram.return_value = TELEGRAM_SUCCESS
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute(
            """UPDATE movies SET title = ?, original_title = ?, overview = ?,
               poster_url = CASE WHEN ? THEN poster_url END WHERE id = 1""",
            ("Я" * 300, "A" * 300, "Описание " * 300, has_poster),
        )

    response = client.post(f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [335984]})

    assert response.status_code == 201
    telegram.assert_called_once()
    assert telegram.call_args.args[1] == "sendMessage"
    text = telegram.call_args.args[2]["text"]
    assert "…\n\nИмя файла:" in text
    assert (">Постер</a>" in text) == has_poster


@pytest.mark.parametrize("second_reply", [TELEGRAM_SUCCESS, TELEGRAM_REFUSAL])
def test_group_splits_in_order_and_records_only_confirmed_deliveries(
    download_client, second_reply
):
    client, telegram = download_client
    telegram.side_effect = [{"ok": True, "result": {"message_id": 100}}, second_reply]
    with client.app.state.movie_repository.database.connect() as connection:
        connection.execute(
            "UPDATE movies SET title = ?, original_title = ?",
            ("🎬" * 300, "A" * 300),
        )
    tmdb_ids = [335984, 329865, 438631, 264660, 157336]

    response = client.post(
        f"{REQUESTS}/by-tmdb", json={"tmdbMovieIds": [*tmdb_ids, tmdb_ids[0]]}
    )

    first, second = [call.args[2]["text"] for call in telegram.call_args_list]
    assert "5 фильмов" in first and "5 фильмов" in second
    assert all((first + second).count(f"CL-{index:06d}_") == 1 for index in range(1, 6))
    assert "<b>3. " in first and "<b>4. " in second
    saved = {item["tmdbMovieId"]: item["telegramMessageId"] for item in client.get(REQUESTS).json()}
    if second_reply["ok"]:
        assert response.status_code == 201
        assert [item["movie"]["tmdbId"] for item in response.json()] == tmdb_ids
        assert [saved[tmdb_id] for tmdb_id in tmdb_ids] == [100, 100, 100, 101, 101]
    else:
        assert response.status_code == 502
        assert "3 из 5" in response.json()["detail"]
        assert saved == dict.fromkeys(tmdb_ids[:3], 100)
