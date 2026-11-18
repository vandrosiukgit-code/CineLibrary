
import { useEffect, useState } from 'react'
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

  const [selectedPerson, setSelectedPerson] = useState<
    (typeof people)[number] | null
  >(null)

  useEffect(() => {
    document.body.style.overflow = selectedMovie ? 'hidden' : ''

    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedMovie])

  useEffect(() => {
    if (!selectedMovie) {
      setSelectedPerson(null)
    }
  }, [selectedMovie])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (selectedPerson) {
          setSelectedPerson(null)
        } else if (selectedMovie) {
          setSelectedMovie(null)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [selectedMovie, selectedPerson])

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

            <div className="movie-modal-top">
              <div className="movie-modal-poster-wrap">
                <img
                  className="movie-modal-poster"
                  src={selectedMovie.poster}
                  alt={selectedMovie.title}
                />

                <div
                  className={`movie-modal-status status-${selectedMovie.availability}`}
                >
                  <span className="availability-dot" />
                  {availabilityLabels[selectedMovie.availability]}
                </div>

                <div className="movie-modal-flags">
                  {selectedMovie.watched && (
                    <span className="modal-flag watched-flag">
                      ✓ Просмотрен
                    </span>
                  )}

                  {selectedMovie.inWishlist && (
                    <span className="modal-flag wishlist-flag">
                      ♡ В списке желаний
                    </span>
                  )}

                  {selectedMovie.isNew && (
                    <span className="modal-flag new-flag">
                      NEW
                    </span>
                  )}
                </div>
              </div>

              <div className="movie-modal-summary">
                <div className="eyebrow">
                  ИНФОРМАЦИЯ О ФИЛЬМЕ
                </div>

                <h2>{selectedMovie.title}</h2>

                {selectedMovie.originalTitle && (
                  <p className="movie-original-title">
                    {selectedMovie.originalTitle}
                  </p>
                )}

                <div className="movie-modal-meta">
                  <span>{selectedMovie.year}</span>
                  <span className="meta-separator">•</span>
                  <span>{selectedMovie.genre}</span>
                </div>

                <div className="movie-modal-rating">
                  <span>★</span>
                  {selectedMovie.rating.toFixed(1)}
                  <small>Рейтинг фильма</small>
                </div>

                <div className="movie-modal-genres">
                  {(selectedMovie.genres || [selectedMovie.genre]).map(
                    (genre) => (
                      <span className="movie-detail-tag" key={genre}>
                        {genre}
                      </span>
                    ),
                  )}
                </div>
              </div>
            </div>

            <div className="movie-modal-body">
              <section className="movie-modal-section movie-description">
                <h3>О фильме</h3>
                <p>
                  {selectedMovie.overview || 'Описание пока отсутствует.'}
                </p>
              </section>

              <div className="movie-modal-columns">
                <section className="movie-modal-section">
                  <h3>Режиссёр</h3>

                  {director ? (
                    <button
                      type="button"
                      className="movie-person-link"
                      onClick={() => setSelectedPerson(director)}
                    >
                      {director.name}
                    </button>
                  ) : (
                    <p>Информация о режиссёре отсутствует.</p>
                  )}
                </section>

                <section className="movie-modal-section">
                  <h3>Актёрский состав</h3>

                  {actors.length > 0 ? (
                    <div className="movie-people-list">
                      {actors.map((actor) => (
                        <button
                          type="button"
                          className="movie-person-link"
                          key={actor.id}
                          onClick={() => setSelectedPerson(actor)}
                        >
                          {actor.name}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p>Информация об актёрах отсутствует.</p>
                  )}
                </section>
              </div>

              <section className="movie-modal-section">
                <h3>Статус в каталоге</h3>

                <div
                  className={`movie-modal-status status-${selectedMovie.availability}`}
                >
                  <span className="availability-dot" />
                  {availabilityLabels[selectedMovie.availability]}
                </div>
              </section>

              <section className="movie-modal-section personal-section">
                <h3>Мои отметки</h3>

                <div className="personal-rating-block">
                  <span>Просмотрен</span>
                  <strong>
                    {selectedMovie.watched ? 'Да' : 'Нет'}
                  </strong>
                </div>

                <div className="personal-rating-block">
                  <span>Моя оценка</span>

                  <strong>
                    {selectedMovie.personalRating !== null
                      ? `★ ${selectedMovie.personalRating} из 5`
                      : 'Ещё не оценён'}
                  </strong>
                </div>

                <div className="personal-rating-block">
                  <span>Список желаний</span>
                  <strong>
                    {selectedMovie.inWishlist ? 'Добавлен' : 'Не добавлен'}
                  </strong>
                </div>

                {selectedMovie.feedbackTags.length > 0 ? (
                  <div className="movie-detail-tags">
                    {selectedMovie.feedbackTags.map((tag) => (
                      <span className="movie-detail-tag" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p>Впечатления пока не добавлены.</p>
                )}

                {selectedMovie.comment && (
                  <div className="movie-comment">
                    <span>Мой комментарий</span>
                    <p>{selectedMovie.comment}</p>
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>
      )}

      {selectedPerson && (
        <div
          className="person-modal-overlay"
          onClick={() => setSelectedPerson(null)}
        >
          <div
            className="person-modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              selectedPerson.role === 'director'
                ? `Карточка режиссёра ${selectedPerson.name}`
                : `Карточка актёра ${selectedPerson.name}`
            }
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="movie-modal-close"
              onClick={() => setSelectedPerson(null)}
              aria-label="Закрыть карточку"
            >
              ×
            </button>

            <div className="eyebrow">
              {selectedPerson.role === 'director'
                ? 'РЕЖИССЁР'
                : 'АКТЁР'}
            </div>

            <h2>{selectedPerson.name}</h2>

            <p>
              Справочная карточка. Состав информации определим позже.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
