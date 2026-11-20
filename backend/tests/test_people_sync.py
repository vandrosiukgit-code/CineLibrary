from app.database import MovieDatabase
from app.repositories.people import PeopleRepository
from app.services.people_sync import PeopleSynchronizer


class FakeTMDB:
    def __init__(self):
        self.person_calls = 0

    def get_movie_credits(self, tmdb_id):
        assert tmdb_id == 100
        return {
            "cast": [
                {
                    "id": 200,
                    "name": "Test Actor",
                    "order": 0,
                    "credit_id": "cast-credit",
                    "character": "Hero",
                }
            ],
            "crew": [],
        }

    def get_person_bundle(self, person_id):
        assert person_id == 200
        self.person_calls += 1
        return {
            "id": 200,
            "name": "Test Actor",
            "also_known_as": ["Actor Test"],
            "biography": "Biography",
            "birthday": "1980-01-02",
            "deathday": None,
            "place_of_birth": "Test City",
            "gender": 2,
            "known_for_department": "Acting",
            "profile_path": "/profile.jpg",
            "homepage": None,
            "external_ids": {
                "imdb_id": "nm0000200",
                "wikidata_id": "Q200",
            },
            "translations": {"translations": []},
            "movie_credits": {
                "cast": [
                    {
                        "id": 100,
                        "credit_id": "cast-credit",
                        "title": "Тестовый фильм",
                        "original_title": "Test Movie",
                        "release_date": "2020-03-04",
                        "character": "Hero",
                        "poster_path": "/poster.jpg",
                        "vote_average": 7.5,
                        "popularity": 10,
                    }
                ],
                "crew": [],
            },
        }


def create_movie(database):
    with database.connect() as connection:
        movie_id = connection.execute(
            """
            INSERT INTO movies (
                title, original_title, release_year, tmdb_id, overview, is_new
            ) VALUES ('Тестовый фильм', 'Test Movie', 2020, 100, '', 0)
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO movie_credits (
                movie_id, canonical_name, display_name, credit_type, sort_order
            ) VALUES (?, 'Test Actor', 'Test Actor', 'actor', 0)
            """,
            (movie_id,),
        )
        return movie_id


def test_people_sync_creates_card_links_movie_and_skips_fresh_profile(tmp_path):
    database = MovieDatabase(tmp_path / "people-test.db")
    database.initialize()
    movie_id = create_movie(database)
    repository = PeopleRepository(database)
    tmdb = FakeTMDB()
    synchronizer = PeopleSynchronizer(tmdb, repository)

    first = synchronizer.sync_movie(movie_id, 100)
    second = synchronizer.sync_movie(movie_id, 100)

    with database.connect() as connection:
        connection.execute(
            "UPDATE people SET next_refresh_at = '2000-01-01 00:00:00+00:00'"
        )
    third = synchronizer.sync_movie(movie_id, 100)

    assert first["people_created"] == 1
    assert first["links_updated"] == 1
    assert second["people_skipped"] == 1
    assert third["people_refreshed"] == 1
    assert tmdb.person_calls == 2

    with database.connect() as connection:
        credit = connection.execute(
            "SELECT person_id, character FROM movie_credits WHERE movie_id = ?",
            (movie_id,),
        ).fetchone()
    assert credit["person_id"] is not None
    assert credit["character"] == "Hero"

    person = repository.get_person(credit["person_id"])
    assert person["name"] == "Test Actor"
    assert person["profile_url"].endswith("/profile.jpg")
    assert person["last_refreshed_at"]
    assert person["filmography"][0]["local_movie_id"] == movie_id
