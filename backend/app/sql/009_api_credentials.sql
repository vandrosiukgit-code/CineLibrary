CREATE TABLE IF NOT EXISTS api_credentials (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    replicate_api_token TEXT NOT NULL,
    tmdb_read_access_token TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (9);
