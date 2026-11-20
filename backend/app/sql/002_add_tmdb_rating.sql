ALTER TABLE movies
ADD COLUMN tmdb_rating REAL
CHECK (tmdb_rating IS NULL OR tmdb_rating BETWEEN 0 AND 10);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (2);
