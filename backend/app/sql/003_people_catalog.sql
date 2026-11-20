CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    tmdb_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    also_known_as TEXT NOT NULL DEFAULT '[]',
    biography TEXT NOT NULL DEFAULT '',
    birthday TEXT,
    deathday TEXT,
    place_of_birth TEXT,
    gender INTEGER,
    known_for_department TEXT,
    profile_url TEXT,
    homepage TEXT,
    imdb_id TEXT,
    wikidata_id TEXT,
    last_refreshed_at TEXT NOT NULL,
    next_refresh_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS person_filmography (
    id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    credit_key TEXT NOT NULL,
    tmdb_movie_id INTEGER NOT NULL,
    local_movie_id INTEGER REFERENCES movies(id) ON DELETE SET NULL,
    credit_kind TEXT NOT NULL CHECK (credit_kind IN ('cast', 'crew')),
    title TEXT NOT NULL,
    original_title TEXT NOT NULL,
    release_year INTEGER,
    character TEXT,
    department TEXT,
    job TEXT,
    poster_url TEXT,
    vote_average REAL,
    popularity REAL,
    UNIQUE (person_id, credit_key)
);

ALTER TABLE movie_credits ADD COLUMN tmdb_credit_id TEXT;
ALTER TABLE movie_credits ADD COLUMN character TEXT;
ALTER TABLE movie_credits ADD COLUMN department TEXT;
ALTER TABLE movie_credits ADD COLUMN job TEXT;

CREATE INDEX IF NOT EXISTS idx_people_tmdb_id ON people(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_people_next_refresh ON people(next_refresh_at);
CREATE INDEX IF NOT EXISTS idx_person_filmography_person_year
    ON person_filmography(person_id, release_year DESC);
CREATE INDEX IF NOT EXISTS idx_person_filmography_tmdb_movie
    ON person_filmography(tmdb_movie_id);
CREATE INDEX IF NOT EXISTS idx_movie_credits_person ON movie_credits(person_id);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (3);
