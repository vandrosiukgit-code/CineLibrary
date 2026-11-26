CREATE TABLE IF NOT EXISTS movie_dna_estimates (
    tmdb_id INTEGER NOT NULL REFERENCES movies(tmdb_id) ON DELETE CASCADE,
    dataset_version TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    result_json TEXT,
    claim_token TEXT,
    claim_until INTEGER,
    PRIMARY KEY (tmdb_id, dataset_version, algorithm_version),
    CHECK (
        (result_json IS NOT NULL AND claim_token IS NULL AND claim_until IS NULL)
        OR (result_json IS NULL AND claim_token IS NOT NULL AND claim_until IS NOT NULL)
    )
);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (10);
