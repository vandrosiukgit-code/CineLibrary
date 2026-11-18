PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    original_title TEXT NOT NULL,
    release_year INTEGER NOT NULL CHECK (release_year BETWEEN 1888 AND 2200),
    tmdb_id INTEGER UNIQUE,
    imdb_id TEXT UNIQUE,
    runtime_minutes INTEGER CHECK (runtime_minutes IS NULL OR runtime_minutes > 0),
    original_language TEXT,
    overview TEXT NOT NULL DEFAULT '',
    poster_url TEXT,
    certification_country TEXT,
    certification_rating TEXT,
    imdb_rating REAL CHECK (imdb_rating IS NULL OR imdb_rating BETWEEN 0 AND 10),
    is_new INTEGER NOT NULL DEFAULT 0 CHECK (is_new IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (certification_country IS NULL AND certification_rating IS NULL)
        OR (certification_country IS NOT NULL AND certification_rating IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE IF NOT EXISTS movie_credits (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    person_id INTEGER,
    canonical_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    credit_type TEXT NOT NULL CHECK (
        credit_type IN (
            'director', 'writer', 'cinematographer', 'composer', 'actor',
            'producer', 'editor', 'production_designer', 'other'
        )
    ),
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS movie_production_companies (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (movie_id, company_name)
);

CREATE TABLE IF NOT EXISTS movie_sources (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    notes TEXT,
    UNIQUE (movie_id, source_name, source_url)
);

CREATE TABLE IF NOT EXISTS movie_user_data (
    movie_id INTEGER PRIMARY KEY REFERENCES movies(id) ON DELETE CASCADE,
    watched INTEGER NOT NULL DEFAULT 0 CHECK (watched IN (0, 1)),
    personal_rating INTEGER CHECK (personal_rating IS NULL OR personal_rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL DEFAULT '',
    in_wishlist INTEGER NOT NULL DEFAULT 0 CHECK (in_wishlist IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS movie_tags (
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE RESTRICT,
    PRIMARY KEY (movie_id, tag_id)
);

CREATE TABLE IF NOT EXISTS movie_files (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    file_path TEXT,
    file_name TEXT,
    file_size INTEGER CHECK (file_size IS NULL OR file_size >= 0),
    file_format TEXT,
    added_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('available', 'downloading', 'missing'))
);

CREATE INDEX IF NOT EXISTS idx_movies_release_year ON movies(release_year);
CREATE INDEX IF NOT EXISTS idx_movies_original_title ON movies(original_title);
CREATE INDEX IF NOT EXISTS idx_movie_credits_name ON movie_credits(canonical_name);
CREATE INDEX IF NOT EXISTS idx_movie_credits_type ON movie_credits(credit_type);
CREATE INDEX IF NOT EXISTS idx_movie_files_movie_status ON movie_files(movie_id, status);
CREATE INDEX IF NOT EXISTS idx_movie_user_data_flags ON movie_user_data(watched, in_wishlist);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (1);
