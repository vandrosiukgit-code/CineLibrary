ALTER TABLE tags ADD COLUMN code TEXT;
ALTER TABLE tags ADD COLUMN category TEXT;
ALTER TABLE tags ADD COLUMN sentiment INTEGER;
ALTER TABLE tags ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_code
    ON tags(code) WHERE code IS NOT NULL;

INSERT OR IGNORE INTO tags (name, code, category, sentiment, sort_order) VALUES
    ('Захватил', 'viewing:captivating', 'viewing', 1, 10),
    ('Смотрелось легко', 'viewing:easy', 'viewing', 1, 20),
    ('Медленно, но интересно', 'viewing:slow_but_good', 'viewing', 1, 30),
    ('Затянуто', 'viewing:dragged', 'viewing', -1, 40),
    ('Скучно', 'viewing:boring', 'viewing', -1, 50),
    ('Не досмотрел', 'viewing:unfinished', 'viewing', -1, 60),
    ('Тронул', 'emotion:moved', 'emotion', 1, 10),
    ('Рассмешил', 'emotion:amused', 'emotion', 1, 20),
    ('Держал в напряжении', 'emotion:tense', 'emotion', 1, 30),
    ('Создал уют', 'emotion:cozy', 'emotion', 1, 40),
    ('Вдохновил', 'emotion:inspired', 'emotion', 1, 50),
    ('Расстроил', 'emotion:saddened', 'emotion', 0, 60),
    ('Напугал', 'emotion:scared', 'emotion', 0, 70),
    ('Оставил послевкусие', 'emotion:lingering', 'emotion', 1, 80),
    ('Сюжет', 'strength:story', 'strength', 1, 10),
    ('Персонажи', 'strength:characters', 'strength', 1, 20),
    ('Актёрская игра', 'strength:acting', 'strength', 1, 30),
    ('Диалоги', 'strength:dialogue', 'strength', 1, 40),
    ('Атмосфера', 'strength:atmosphere', 'strength', 1, 50),
    ('Визуальный стиль', 'strength:visuals', 'strength', 1, 60),
    ('Музыка', 'strength:music', 'strength', 1, 70),
    ('Финал', 'strength:ending', 'strength', 1, 80),
    ('Сюжет', 'weakness:story', 'weakness', -1, 10),
    ('Персонажи', 'weakness:characters', 'weakness', -1, 20),
    ('Актёрская игра', 'weakness:acting', 'weakness', -1, 30),
    ('Диалоги', 'weakness:dialogue', 'weakness', -1, 40),
    ('Атмосфера', 'weakness:atmosphere', 'weakness', -1, 50),
    ('Визуальный стиль', 'weakness:visuals', 'weakness', -1, 60),
    ('Музыка', 'weakness:music', 'weakness', -1, 70),
    ('Финал', 'weakness:ending', 'weakness', -1, 80),
    ('Хочу пересмотреть', 'outcome:rewatch', 'outcome', 1, 10),
    ('Достаточно одного просмотра', 'outcome:once_enough', 'outcome', -1, 20);

INSERT OR IGNORE INTO schema_migrations(version) VALUES (4);
