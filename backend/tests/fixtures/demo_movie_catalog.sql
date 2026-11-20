INSERT INTO genres (id, canonical_name, display_name) VALUES
    (1, 'Science Fiction', 'Фантастика'),
    (2, 'Drama', 'Драма'),
    (3, 'Thriller', 'Триллер'),
    (4, 'Mystery', 'Детектив'),
    (5, 'Adventure', 'Приключения');

INSERT INTO tags (id, name) VALUES
    (1001, 'Хорошая атмосфера'),
    (1002, 'Оригинальная идея'),
    (1003, 'Интересный сюжет'),
    (1004, 'Эмоциональная глубина');

INSERT INTO movies (
    id, title, original_title, release_year, tmdb_id, imdb_id,
    overview, poster_url, imdb_rating, is_new
) VALUES
    (1, 'Бегущий по лезвию 2049', 'Blade Runner 2049', 2017, 335984, 'tt1856101',
     'Молодой офицер полиции раскрывает тайну, способную изменить представление человечества о собственном существовании.',
     'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg', 8.0, 0),
    (2, 'Прибытие', 'Arrival', 2016, 329865, 'tt2543164',
     'Лингвист пытается установить контакт с инопланетной цивилизацией, прибывшей на Землю.',
     'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg', 7.9, 0),
    (3, 'Дюна', 'Dune', 2021, 438631, 'tt1160419',
     'История Пола Атрейдеса и его путешествия на пустынную планету Арракис.',
     'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg', 8.0, 0),
    (4, 'Из машины', 'Ex Machina', 2014, 264660, 'tt0470752',
     'Программист участвует в эксперименте по проверке возможностей искусственного интеллекта.',
     'https://image.tmdb.org/t/p/w500/dmJW8IAKHKxFNiUnoDR7JfsK7Rp.jpg', 7.7, 1),
    (5, 'Интерстеллар', 'Interstellar', 2014, 157336, 'tt0816692',
     'Группа исследователей отправляется через червоточину на поиски нового дома для человечества.',
     'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg', 8.7, 1);

INSERT INTO movie_genres (movie_id, genre_id, sort_order) VALUES
    (1, 1, 0), (1, 2, 1), (1, 3, 2),
    (2, 1, 0), (2, 2, 1), (2, 4, 2),
    (3, 1, 0), (3, 5, 1), (3, 2, 2),
    (4, 1, 0), (4, 3, 1), (4, 2, 2),
    (5, 1, 0), (5, 5, 1), (5, 2, 2);

INSERT INTO movie_credits (
    movie_id, canonical_name, display_name, credit_type, sort_order
) VALUES
    (1, 'Denis Villeneuve', 'Дени Вильнёв', 'director', 0),
    (1, 'Ryan Gosling', 'Райан Гослинг', 'actor', 0),
    (2, 'Denis Villeneuve', 'Дени Вильнёв', 'director', 0),
    (2, 'Amy Adams', 'Эми Адамс', 'actor', 0),
    (3, 'Denis Villeneuve', 'Дени Вильнёв', 'director', 0),
    (3, 'Timothée Chalamet', 'Тимоти Шаламе', 'actor', 0),
    (4, 'Alex Garland', 'Алекс Гарленд', 'director', 0),
    (4, 'Alicia Vikander', 'Алисия Викандер', 'actor', 0),
    (5, 'Christopher Nolan', 'Кристофер Нолан', 'director', 0),
    (5, 'Matthew McConaughey', 'Мэттью Макконахи', 'actor', 0);

INSERT INTO movie_user_data (
    movie_id, watched, personal_rating, comment, in_wishlist
) VALUES
    (1, 1, 5, '', 0),
    (2, 1, 5, '', 0),
    (3, 0, NULL, '', 1),
    (4, 0, NULL, '', 1),
    (5, 1, 5, '', 0);

INSERT INTO movie_tags (movie_id, tag_id) VALUES
    (1, 1001), (1, 1002),
    (2, 1003), (2, 1004),
    (5, 1003), (5, 1004);

INSERT INTO movie_files (movie_id, status) VALUES
    (1, 'available'),
    (2, 'available'),
    (3, 'downloading'),
    (4, 'missing'),
    (5, 'available');

INSERT INTO movie_sources (movie_id, source_name, source_url, checked_at) VALUES
    (1, 'IMDb', 'https://www.imdb.com/title/tt1856101/', '2026-11-18'),
    (1, 'TMDB', 'https://www.themoviedb.org/movie/335984', '2026-11-18'),
    (2, 'IMDb', 'https://www.imdb.com/title/tt2543164/', '2026-11-18'),
    (2, 'TMDB', 'https://www.themoviedb.org/movie/329865', '2026-11-18'),
    (3, 'IMDb', 'https://www.imdb.com/title/tt1160419/', '2026-11-18'),
    (3, 'TMDB', 'https://www.themoviedb.org/movie/438631', '2026-11-18'),
    (4, 'IMDb', 'https://www.imdb.com/title/tt0470752/', '2026-11-18'),
    (4, 'TMDB', 'https://www.themoviedb.org/movie/264660', '2026-11-18'),
    (5, 'IMDb', 'https://www.imdb.com/title/tt0816692/', '2026-11-18'),
    (5, 'TMDB', 'https://www.themoviedb.org/movie/157336', '2026-11-18');
