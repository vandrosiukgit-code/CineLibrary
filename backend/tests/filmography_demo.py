"""Offline browser check. From backend run: python -m tests.filmography_demo"""

import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import uvicorn
from fastapi import Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.clients.tmdb import TMDBClient
from app.database import MovieDatabase
from app.main import create_app
from app.services.telegram_delivery import TelegramDeliveryService


DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SEED = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"
REQUEST_PATH = "/api/movies/download-requests/by-tmdb"


def prepare_demo(db):
    db.initialize()
    db.seed(SEED)
    with db.connect() as connection:
        person_id = connection.execute(
            """INSERT INTO people (tmdb_id, name, display_name, last_refreshed_at, next_refresh_at)
               VALUES (999, 'Denis Villeneuve', 'Дени Вильнёв', CURRENT_TIMESTAMP, '2099-01-01')"""
        ).lastrowid
        connection.execute(
            "UPDATE movie_credits SET person_id = ? WHERE canonical_name = 'Denis Villeneuve'",
            (person_id,),
        )
        connection.execute(
            """INSERT INTO person_filmography
               (person_id, credit_key, tmdb_movie_id, local_movie_id, credit_kind, title, original_title)
               SELECT ?, original_title, tmdb_id, id, 'crew', title, original_title
               FROM movies WHERE id IN (1, 2)""",
            (person_id,),
        )
        connection.execute("UPDATE movie_files SET status = 'missing' WHERE movie_id IN (1, 2)")
    TelegramDeliveryService(db).save_settings("demo-token", "demo-chat")


def show_state(db, step):
    with db.connect() as connection:
        rows = connection.execute(
            """SELECT m.original_title, f.status, u.in_wishlist, u.watched, u.personal_rating,
                      r.telegram_message_id
               FROM movies m JOIN movie_files f ON f.movie_id = m.id
               JOIN movie_user_data u ON u.movie_id = m.id
               LEFT JOIN movie_download_requests r ON r.local_movie_id = m.id
               WHERE m.id IN (1, 2) ORDER BY m.id"""
        )
        print(step, [tuple(row) for row in rows], flush=True)


def main():
    if not (DIST / "index.html").is_file():
        raise SystemExit("Run npm run build in frontend first.")
    with TemporaryDirectory(prefix="cinelibrary-demo-") as directory:
        db = MovieDatabase(Path(directory) / "demo.db")
        prepare_demo(db)
        app = create_app(db.path)

        @app.middleware("http")
        async def isolate_demo(request: Request, call_next):
            submitting = request.method == "POST" and request.url.path == REQUEST_PATH
            if request.method != "GET" and not submitting:
                return Response(status_code=405)
            if submitting:
                show_state(db, "before POST")
            try:
                response = await call_next(request)
            except Exception:
                if submitting:
                    show_state(db, "after unhandled exception")
                raise
            if submitting:
                show_state(db, f"after HTTP {response.status_code}")
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"
            )
            return response

        @app.get("/assets/{name}.js")
        def demo_bundle(name: str):
            # The production client uses port 8000. Only the served demo copy targets this origin.
            bundle = DIST / "assets" / f"{name}.js"
            if bundle.parent.resolve() != (DIST / "assets").resolve() or not bundle.is_file():
                return Response(status_code=404)
            data = bundle.read_bytes().replace(b"http://127.0.0.1:8000/api/", b"/api/")
            return Response(data, media_type="text/javascript")

        app.mount("/", StaticFiles(directory=DIST), name="demo-ui")

        def telegram_reply(_service, _token, method, payload):
            if method not in {"sendMessage", "sendPhoto"}:
                raise ValueError(f"Unexpected Telegram method: {method}")
            show_state(db, f"at {method}")
            text = payload.get("text") or payload["caption"]
            print("transport:", method, repr(text), flush=True)
            if "CL-000002_Arrival" in text:
                return {"ok": False, "description": "Demo delivery refused"}
            return {"ok": True, "result": {"message_id": 101}}

        # Both targets already exist in the fixture. Only a credits lookup is expected.
        with (
            patch.object(TMDBClient, "from_environment", autospec=True) as tmdb,
            patch.object(TelegramDeliveryService, "_call", telegram_reply),
        ):
            tmdb.return_value.get_movie_credits.return_value = {"cast": [], "crew": []}
            print("Demo: http://127.0.0.1:18080/index.html", flush=True)
            uvicorn.run(app, host="127.0.0.1", port=18080)
        # SQLite connection contexts commit but can keep handles until cyclic GC on Windows.
        gc.collect()


if __name__ == "__main__":
    main()
