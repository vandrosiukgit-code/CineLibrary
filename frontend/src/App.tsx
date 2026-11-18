
import { useEffect, useState } from 'react'
import './App.css'
import {
  loadMovies,
  saveUserData,
  type LibraryFilter,
  type MovieView,
} from './data/movieApi'
import type { MovieCredit, MovieUserDataUpdate } from './data/movieCatalog'

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
  const [movies, setMovies] = useState<MovieView[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<LibraryFilter>('all')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedMovie, setSelectedMovie] = useState<MovieView | null>(null)
  const [selectedPerson, setSelectedPerson] = useState<MovieCredit | null>(null)

  const closeMovie = () => {
    setSelectedPerson(null)
    setSelectedMovie(null)
  }

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setIsLoading(true)
      setError('')
      loadMovies(search, filter, controller.signal)
        .then(setMovies)
        .catch((requestError: unknown) => {
          if (requestError instanceof DOMException && requestError.name === 'AbortError') {
            return
          }
          setError('Не удалось подключиться к базе фильмов. Запустите backend.')
        })
        .finally(() => setIsLoading(false))
    }, 200)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [search, filter])

  useEffect(() => {
    document.body.style.overflow = selectedMovie ? 'hidden' : ''

    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedMovie])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (selectedPerson) {
          setSelectedPerson(null)
        } else if (selectedMovie) {
          closeMovie()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [selectedMovie, selectedPerson])

  const director = selectedMovie?.director ?? null
  const actors = selectedMovie?.actors ?? []

  const applyUserData = async (
    movie: MovieView,
    changes: MovieUserDataUpdate,
  ) => {
    try {
      const updatedMovie = await saveUserData(movie.id, changes)
      setMovies((currentMovies) =>
        currentMovies.map((item) =>
          item.id === updatedMovie.id ? updatedMovie : item,
        ),
      )
      setSelectedMovie(updatedMovie)
      setError('')
    } catch {
      setError('Не удалось сохранить личные отметки.')
    }
  }

  const selectMenuItem = (index: number) => {
    if (index === 2) setFilter('watched')
    else if (index === 3) setFilter('wishlist')
    else if (index <= 1) setFilter('all')
    setIsMenuOpen(false)
  }

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
              className={`nav-item ${
                (filter === 'all' && index === 0) ||
                (filter === 'watched' && index === 2) ||
                (filter === 'wishlist' && index === 3)
                  ? 'active'
                  : ''
              }`}
              key={item.label}
              onClick={() => selectMenuItem(index)}
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

          <div className="library-controls">
            <label className="search-field">
              <span className="visually-hidden">Поиск фильмов</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Название фильма"
              />
            </label>

            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value as LibraryFilter)}
              aria-label="Фильтр библиотеки"
            >
              <option value="all">Все фильмы</option>
              <option value="watched">Просмотренные</option>
              <option value="wishlist">Список желаний</option>
              <option value="available">На диске</option>
              <option value="downloading">Скачиваются</option>
              <option value="missing">Нет на диске</option>
            </select>
          </div>

          {error && <div className="library-message error-message">{error}</div>}

          {isLoading && (
            <div className="library-message">Загрузка библиотеки…</div>
          )}

          {!isLoading && !error && movies.length === 0 && (
            <div className="library-message">Фильмы не найдены.</div>
          )}

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
                      src={movie.poster ?? undefined}
                      alt={movie.title}
                    />

                    {movie.rating !== null && (
                      <div className="movie-rating">
                        ★ {movie.rating.toFixed(1)}
                      </div>
                    )}

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
          onClick={closeMovie}
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
              onClick={closeMovie}
              aria-label="Закрыть карточку"
            >
              ×
            </button>

            <div className="movie-modal-top">
              <div className="movie-modal-poster-wrap">
                <img
                  className="movie-modal-poster"
                  src={selectedMovie.poster ?? undefined}
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

                {selectedMovie.rating !== null && (
                  <div className="movie-modal-rating">
                    <span>★</span>
                    {selectedMovie.rating.toFixed(1)}
                    <small>Рейтинг IMDb</small>
                  </div>
                )}

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
                      {director.displayName}
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
                          {actor.displayName}
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

                <div className="personal-actions">
                  <button
                    type="button"
                    onClick={() =>
                      applyUserData(selectedMovie, {
                        watched: !selectedMovie.watched,
                      })
                    }
                  >
                    {selectedMovie.watched
                      ? 'Отметить непросмотренным'
                      : 'Отметить просмотренным'}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      applyUserData(selectedMovie, {
                        inWishlist: !selectedMovie.inWishlist,
                      })
                    }
                  >
                    {selectedMovie.inWishlist
                      ? 'Убрать из желаний'
                      : 'Добавить в желания'}
                  </button>

                  <label>
                    <span>Моя оценка</span>
                    <select
                      value={selectedMovie.personalRating ?? ''}
                      onChange={(event) =>
                        applyUserData(selectedMovie, {
                          personalRating: event.target.value
                            ? Number(event.target.value)
                            : null,
                        })
                      }
                    >
                      <option value="">Без оценки</option>
                      {[1, 2, 3, 4, 5].map((rating) => (
                        <option value={rating} key={rating}>
                          {rating} из 5
                        </option>
                      ))}
                    </select>
                  </label>
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
              selectedPerson.creditType === 'director'
                ? `Карточка режиссёра ${selectedPerson.displayName}`
                : `Карточка актёра ${selectedPerson.displayName}`
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
              {selectedPerson.creditType === 'director'
                ? 'РЕЖИССЁР'
                : 'АКТЁР'}
            </div>

            <h2>{selectedPerson.displayName}</h2>

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
