
import { useState } from 'react'
import './App.css'
import { movies, people } from './data/movies'

const menuItems = [
  { icon: '⌂', label: 'Главная' },
  { icon: '▤', label: 'Моя библиотека' },
  { icon: '✓', label: 'Просмотренные' },
  { icon: '◷', label: 'Смотреть позже' },
  { icon: '▦', label: 'Коллекции' },
  { icon: '◇', label: 'Жанры' },
  { icon: '✧', label: 'Рекомендации' },
]

const availabilityLabels = {
  available: 'На диске',
  downloading: 'Скачивается',
  missing: 'Нет на диске',
}

function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [selectedMovie, setSelectedMovie] = useState<
    (typeof movies)[number] | null
  >(null)

  const director = selectedMovie
    ? people.find((person) => person.id === selectedMovie.directorId)
    : null

  const actors = selectedMovie
    ? people.filter((person) =>
        selectedMovie.actorIds.includes(person.id),
      )
    : []

  return (
    <div className="app-shell">
      {isMenuOpen && (
        <div
          className="menu-overlay"
          onClick={() => setIsMenuOpen(false)}
        />
      )}

      <aside className={`sidebar ${isMenuOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-icon">C</div>
          <span>CineLibrary</span>
        </div>

        <div className="sidebar-label">МЕНЮ</div>

        <nav className="navigation">
          {menuItems.map((item, index) => (
            <button
              className={`nav-item ${index === 0 ? 'active' : ''}`}
              key={item.label}
              onClick={() => setIsMenuOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span className="nav-icon">⚙</span>
            <span>Настройки</span>
          </button>

          <div className="sidebar-version">
            CineLibrary · версия 0.1
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <button
            className="menu-toggle"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Открыть меню"
          >
            ☰
          </button>

          <div className="breadcrumb">
            Моя коллекция / Главная
          </div>

          <div className="profile">
            <div className="profile-avatar">U</div>
          </div>
        </header>

        <section className="welcome-section">
          <div>
            <div className="eyebrow">
              ВАША ЛИЧНАЯ КИНОТЕКА
            </div>

            <h1>Добро пожаловать</h1>

            <p>
              Ваша история кино начинается здесь.
            </p>
          </div>

          <button className="add-button">
            ＋ Добавить фильм
          </button>
        </section>

        <section className="content-section">
          <div className="section-heading">
            <div>
              <h2>Моя библиотека</h2>

              <p>
                Фильмы из вашей коллекции
              </p>
            </div>

            <button className="text-button">
              Вся библиотека →
            </button>
          </div>

          <div className="movie-grid">
            {movies.map((movie) => (
              <article
                className="movie-card"
                key={movie.id}
              >
                <button
                  className="movie-poster-button"
                  onClick={() => setSelectedMovie(movie)}
                  aria-label={`Подробнее о фильме ${movie.title}`}
                >
                  <div
                    className={`movie-poster status-${movie.availability}`}
                  >
                    <img
                      src={movie.poster}
                      alt={movie.title}
                    />

                    <div className="movie-rating">
                      ★ {movie.rating.toFixed(1)}
                    </div>

                    {movie.isNew && (
                      <div className="movie-new">
                        NEW
                      </div>
                    )}

                    {movie.watched && (
                      <div
                        className="movie-watched"
                        title="Просмотрено"
                      >
                        ✓
                      </div>
                    )}

                    <div
                      className={`movie-availability availability-${movie.availability}`}
                    >
                      <span className="availability-dot" />
                      {availabilityLabels[movie.availability]}
                    </div>
                  </div>
                </button>

                <div className="movie-info">
                  <h3>{movie.title}</h3>

                  <p>
                    {movie.year} · {movie.genre}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      {selectedMovie && (
        <div
          className="movie-modal-overlay"
          onClick={() => setSelectedMovie(null)}
        >
          <div
            className="movie-modal"
            role="dialog"
            aria-modal="true"
            aria-label={`Информация о фильме ${selectedMovie.title}`}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="movie-modal-close"
              onClick={() => setSelectedMovie(null)}
              aria-label="Закрыть карточку"
            >
              ×
            </button>

            <div className="movie-modal-header">
              <img
                className="movie-modal-poster"
                src={selectedMovie.poster}
                alt={selectedMovie.title}
              />

              <div className="movie-modal-heading">
                <div className="eyebrow">ИНФОРМАЦИЯ О ФИЛЬМЕ</div>

                <h2>{selectedMovie.title}</h2>

                {selectedMovie.originalTitle && (
                  <p className="movie-original-title">
                    {selectedMovie.originalTitle}
                  </p>
                )}

                <p className="movie-modal-year">
                  {selectedMovie.year}
                </p>

                <div className="movie-modal-rating">
                  ★ {selectedMovie.rating.toFixed(1)}
                </div>
              </div>
            </div>

            <div className="movie-modal-content">
              <div className="movie-detail-row">
                <span>Наличие</span>
                <strong>
                  {availabilityLabels[selectedMovie.availability]}
                </strong>
              </div>

              <div className="movie-detail-row">
                <span>Просмотрен</span>
                <strong>
                  {selectedMovie.watched ? 'Да' : 'Нет'}
                </strong>
              </div>

              <div className="movie-detail-row">
                <span>В списке желаний</span>
                <strong>
                  {selectedMovie.inWishlist ? 'Да' : 'Нет'}
                </strong>
              </div>

              <div className="movie-detail-section">
                <h3>Описание</h3>
                <p>{selectedMovie.overview || 'Описание пока отсутствует.'}</p>
              </div>

              <div className="movie-detail-section">
                <h3>Жанры</h3>
                <div className="movie-detail-tags">
                  {(selectedMovie.genres || [selectedMovie.genre]).map(
                    (genre) => (
                      <span className="movie-detail-tag" key={genre}>
                        {genre}
                      </span>
                    ),
                  )}
                </div>
              </div>

              {director && (
                <div className="movie-detail-section">
                  <h3>Режиссёр</h3>
                  <p>
                    {director.name}
                    {director.personalRating !== null &&
                      ` · ★ ${director.personalRating}`}
                  </p>
                </div>
              )}

              <div className="movie-detail-section">
                <h3>Актёры</h3>
                {actors.length > 0 ? (
                  <div className="movie-people-list">
                    {actors.map((actor) => (
                      <div className="movie-person" key={actor.id}>
                        <span>{actor.name}</span>
                        {actor.personalRating !== null && (
                          <span>★ {actor.personalRating}</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p>Информация об актёрах отсутствует.</p>
                )}
              </div>

              <div className="movie-detail-section">
                <h3>Моя оценка</h3>
                <p>
                  {selectedMovie.personalRating !== null
                    ? `★ ${selectedMovie.personalRating} из 5`
                    : 'Ещё не оценён'}
                </p>
              </div>

              {selectedMovie.feedbackTags.length > 0 && (
                <div className="movie-detail-section">
                  <h3>Мои впечатления</h3>
                  <div className="movie-detail-tags">
                    {selectedMovie.feedbackTags.map((tag) => (
                      <span className="movie-detail-tag" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedMovie.comment && (
                <div className="movie-detail-section">
                  <h3>Мой комментарий</h3>
                  <p>{selectedMovie.comment}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
