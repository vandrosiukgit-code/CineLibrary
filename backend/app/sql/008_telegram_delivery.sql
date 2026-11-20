CREATE TABLE IF NOT EXISTS telegram_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    bot_token TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE movie_download_requests ADD COLUMN international_title TEXT;
ALTER TABLE movie_download_requests ADD COLUMN file_name TEXT;
ALTER TABLE movie_download_requests ADD COLUMN telegram_message_id INTEGER;

INSERT OR IGNORE INTO schema_migrations(version) VALUES (8);
