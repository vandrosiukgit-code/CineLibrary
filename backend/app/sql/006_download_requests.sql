CREATE TABLE IF NOT EXISTS movie_download_requests (
    id INTEGER PRIMARY KEY,
    tmdb_movie_id INTEGER NOT NULL UNIQUE,
    local_movie_id INTEGER REFERENCES movies(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'requested'
        CHECK (status IN ('requested', 'completed', 'cancelled')),
    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_movie_download_requests_status
    ON movie_download_requests(status, requested_at DESC);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (6);
