from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.services import media_sync
from app.services.media_scan import scan_media


def touch(root, relative):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def test_scan_recognizes_video_iso_and_optical_structures_as_copies(tmp_path):
    for relative in (
        "CL-000001_Film.MKV", "CL-000001_Film.iso", "notes.txt",
        "DVD/VIDEO_TS/VIDEO_TS.IFO", "DVD/VIDEO_TS/VTS_01_1.VOB",
        "CL-000002_BD/BDMV/index.bdmv", "CL-000002_BD/BDMV/STREAM/00001.m2ts",
        "Incomplete/BDMV/index.bdmv",
    ):
        touch(tmp_path, relative)

    result = scan_media(tmp_path)

    assert not result.errors
    assert {(copy.name, copy.kind, copy.status, copy.cl_id) for copy in result.copies} == {
        ("CL-000001_Film.MKV", "video", "available", "CL-000001"),
        ("CL-000001_Film.iso", "iso", "available", "CL-000001"),
        ("DVD", "dvd", "available", None),
        ("CL-000002_BD", "bluray", "available", "CL-000002"),
        ("Incomplete", "bluray", "unknown", None),
    }


def test_qb_suffix_marks_copy_as_downloading_until_next_scan(tmp_path):
    video = touch(tmp_path, "Film.mp4.!QB")
    iso = touch(tmp_path, "Disc.iso.!qb")
    touch(tmp_path, "DVD/VIDEO_TS/VIDEO_TS.IFO")
    dvd = touch(tmp_path, "DVD/VIDEO_TS/title.vob.!qb")
    touch(tmp_path, "BD/BDMV/index.bdmv")
    bd = touch(tmp_path, "BD/BDMV/STREAM/title.m2ts.!qb")
    touch(tmp_path, "Cover.jpg.!qb")

    assert [copy.status for copy in scan_media(tmp_path).copies] == ["downloading"] * 4
    for path in (video, iso, dvd, bd):
        path.rename(path.with_suffix(""))
    assert [copy.status for copy in scan_media(tmp_path).copies] == ["available"] * 4


def test_exclusions_skip_subtrees_by_full_path_and_report_unreadable_paths(tmp_path, monkeypatch):
    touch(tmp_path, "extras/deep/first.mp4")
    touch(tmp_path, "old/deep/second.mp4")
    touch(tmp_path, "other/extras/deep/third.mp4")
    inaccessible = touch(tmp_path, "unreadable/fourth.mp4").parent
    original_iterdir = Path.iterdir

    def iterdir(path):
        if path == inaccessible:
            raise PermissionError("access denied")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", iterdir)
    result = scan_media(tmp_path, excluded=(Path("extras"), tmp_path / "old"))

    assert [copy.name for copy in result.copies] == ["third.mp4"]
    assert result.errors == {str(inaccessible): "access denied"}
    assert str(tmp_path / "missing") in scan_media(tmp_path / "missing").errors


def test_sync_settings_and_main_action_refresh_catalog_without_ai_for_known_id(tmp_path):
    root = tmp_path / "films"
    film = touch(root, "CL-000004_Ex_Machina.mkv")
    touch(root, "Excluded/Unknown.mp4")
    seed = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"
    route = "/api/agents/movie-librarian-1/media-sync"

    with TestClient(create_app(tmp_path / "test.db", seed_path=seed)) as client:
        assert client.post(route).status_code == 409
        browser = client.get(f"{route}/folders", params={"path": str(root)})
        assert browser.json()["folders"] == [{"name": "Excluded", "path": str(root / "Excluded")}]
        assert browser.json()["parent"] == str(tmp_path)
        assert client.put(f"{route}/settings", json={"root": str(film)}).status_code == 422
        assert client.put(f"{route}/settings", json={"root": str(root), "excluded": [str(film)]}).status_code == 422
        saved = client.put(f"{route}/settings", json={"root": str(root), "excluded": ["Excluded"]})
        assert saved.status_code == 200, saved.text
        assert client.get(f"{route}/settings").json() == saved.json()
        assert client.post(route).json() == {"matched": 1, "pending": [], "errors": {}}
        assert client.get("/api/movies/4").json()["availability"] == "available"
        film.rename(film.with_suffix(".mkv.!qb"))
        client.post(route).raise_for_status()
        assert client.get("/api/movies/4").json()["availability"] == "downloading"
        assert client.put(f"{route}/settings", json={"root": ""}).json() == {"root": "", "excluded": []}
        assert client.post(route).status_code == 409
        assert film.with_suffix(".mkv.!qb").exists()


def test_manual_sync_activates_periodic_availability_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(media_sync, "MEDIA_SYNC_INTERVAL_SECONDS", 0.05)
    root = tmp_path / "films"
    film = touch(root, "CL-000004_Ex_Machina.mkv")
    seed = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"
    route = "/api/agents/movie-librarian-1/media-sync"
    with TestClient(create_app(tmp_path / "test.db", seed_path=seed)) as client:
        client.put(f"{route}/settings", json={"root": str(root)}).raise_for_status()
        assert client.app.state.media_sync_scheduler.worker is None
        client.post(route).raise_for_status()
        assert client.get("/api/movies/4").json()["availability"] == "available"
        touch(root, "Unknown film.mkv")
        film.rename(film.with_suffix(".mkv.!qb"))
        deadline = monotonic() + 3
        while monotonic() < deadline:
            if client.get("/api/movies/4").json()["availability"] == "downloading":
                break
            sleep(0.02)
        else:
            raise AssertionError("Automatic availability check did not update the catalog")


def test_ready_copy_replaces_pathless_download_status_even_if_import_fails(tmp_path):
    root = tmp_path / "films"
    film = touch(root, "CL-000004_Ex_Machina.mkv")
    unknown = touch(root, "Unknown film.mkv")
    seed = Path(__file__).parent / "fixtures" / "demo_movie_catalog.sql"

    def unavailable_importer():
        raise RuntimeError("import unavailable")

    with TestClient(create_app(tmp_path / "test.db", seed_path=seed)) as client:
        movies = client.app.state.movie_repository
        with movies.database.connect() as connection:
            connection.execute("UPDATE movie_files SET status = 'downloading' WHERE movie_id = 4")
        with pytest.raises(RuntimeError, match="import unavailable"):
            media_sync.sync_media(movies, root, (), unavailable_importer)
        assert movies.get_movie(4)["availability"] == "available"
        film.unlink()
        unknown.unlink()
        media_sync.sync_media(movies, root, ())
        assert movies.get_movie(4)["availability"] == "missing"
