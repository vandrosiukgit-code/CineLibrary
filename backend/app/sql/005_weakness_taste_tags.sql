INSERT OR IGNORE INTO tags (name, code, category, sentiment, sort_order) VALUES
    ('Сюжет — не понравился', 'weakness:story', 'weakness', -1, 10),
    ('Персонажи — не понравились', 'weakness:characters', 'weakness', -1, 20),
    ('Актёрская игра — не понравилась', 'weakness:acting', 'weakness', -1, 30),
    ('Диалоги — не понравились', 'weakness:dialogue', 'weakness', -1, 40),
    ('Атмосфера — не понравилась', 'weakness:atmosphere', 'weakness', -1, 50),
    ('Визуальный стиль — не понравился', 'weakness:visuals', 'weakness', -1, 60),
    ('Музыка — не понравилась', 'weakness:music', 'weakness', -1, 70),
    ('Финал — не понравился', 'weakness:ending', 'weakness', -1, 80);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (5);
