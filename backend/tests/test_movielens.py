import sqlite3
from contextlib import closing

import pytest

from app.repositories.movielens import GenomeTag, MovieLensIndex


@pytest.fixture
def csv_dir(tmp_path):
    (tmp_path / "links.csv").write_text(
        "movieId,imdbId,tmdbId\n1,0114709,00862\n1,0114709,862\n"
        "2,0113497,8844\n3,0113228,600\n4,0114885,600\n5,0113041,\n",
        encoding="utf-8",
    )
    (tmp_path / "genome-tags.csv").write_text(
        "tagId,tag\n1,007\n2,absurd\n3,\"funny, dry\"\n", encoding="utf-8"
    )
    (tmp_path / "genome-scores.csv").write_text(
        "movieId,tagId,relevance\n1,3,0.82\n1,1,0.0\n3,1,0.5\n5,1,0.1\n",
        encoding="utf-8",
    )
    return tmp_path


def test_import_and_repeat_read_original_without_filling_missing_tags(csv_dir):
    index = MovieLensIndex(csv_dir / "index.db")
    assert index.get_original(862).status == "index_unavailable"

    for _ in range(2):
        assert index.import_csv(csv_dir, "25m-test") == {
            "links": 4, "tags": 3, "scores": 4, "genomes": 3,
        }
        result = index.get_original(862)
        assert result.status == "found"
        assert (result.tmdb_id, result.movie_id, result.source) == (862, 1, "original")
        assert result.dataset_version == "25m-test"
        assert result.tags == (GenomeTag(1, "007", 0.0), GenomeTag(3, "funny, dry", 0.82))


def test_lookup_distinguishes_unmapped_ambiguous_and_unscored_movies(csv_dir):
    index = MovieLensIndex(csv_dir / "index.db")
    index.import_csv(csv_dir, "25m-test")

    unscored = index.get_original(8844)
    assert unscored.status == "no_original_genome"
    assert unscored.movie_id == 2
    assert unscored.source is None
    assert index.get_original(600).status == "ambiguous_mapping"
    assert index.get_original(9999).status == "no_tmdb_mapping"
    with pytest.raises(ValueError, match="positive"):
        index.get_original(0)


def test_invalid_import_keeps_previous_index(csv_dir):
    index = MovieLensIndex(csv_dir / "index.db")
    index.import_csv(csv_dir, "25m-original")
    (csv_dir / "genome-scores.csv").write_text(
        "movieId,tagId,relevance\n1,1,0.5\n1,99,0.6\n", encoding="utf-8"
    )

    with pytest.raises(sqlite3.IntegrityError):
        index.import_csv(csv_dir, "invalid")

    original = index.get_original(862)
    assert original.dataset_version == "25m-original"
    assert original.tags[-1] == GenomeTag(3, "funny, dry", 0.82)


def test_import_refuses_to_replace_catalog_database(csv_dir):
    path = csv_dir / "catalog.db"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE movies (id INTEGER)")

    with pytest.raises(ValueError, match="non-MovieLens"):
        MovieLensIndex(path).import_csv(csv_dir, "25m-test")

    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT * FROM movies").fetchall() == []
