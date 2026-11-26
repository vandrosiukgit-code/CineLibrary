ALTER TABLE movie_files ADD COLUMN scan_root TEXT;

CREATE TABLE media_sync_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    root TEXT NOT NULL,
    excluded TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (11);
