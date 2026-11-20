
import { useEffect, useRef, useState } from 'react'
import './App.css'
import {
  loadDownloadRequests,
  loadGenres,
  loadTasteTags,
  loadMovies,
  requestMovieDownload,
  saveUserData,
  type LibraryFilter,
  type LibrarySort,
  type MovieView,
  type TasteTagDefinition,
} from './data/movieApi'
import type {
  AvailabilityStatus,
  MovieCredit,
  MovieUserDataUpdate,
} from './data/movieCatalog'
import {
  loadPerson,
  type PersonFilmographyItem,
  type PersonRecord,
} from './data/personApi'
import {
  CineLibraryWordmark,
  getTypographyVariant,
} from './components/TypographyPreview'

interface FilmographyPreview {
  title: string
  originalTitle: string
  year: number | null
  poster: string | null
  genres: string[]
  rating: number | null
  personalRating: number | null
  overview: string
  role: string | null
  inLibrary: boolean
  availability: AvailabilityStatus
  tmdbMovieId: number
  localMovieId: number | null
  top: number
  left: number
  width: number
}

const menuItems = [
  { icon: '▤', label: 'Весь дневник', filter: 'all' },
  { icon: '★', label: 'Оценка 4–5', filter: 'high-rated' },
  { icon: '↻', label: 'Хочу пересмотреть', filter: 'rewatch' },
  { icon: '−', label: 'Не понравилось', filter: 'disliked' },
  { icon: '☆', label: 'Без оценки', filter: 'unrated' },
  { icon: '◇', label: 'Без впечатлений', filter: 'untagged' },
] satisfies { icon: string; label: string; filter: LibraryFilter }[]

const availabilityLabels = {
  available: 'На диске',
  downloading: 'Скачивается',
  missing: 'Нет на диске',
}

const configuratorCards = [
  'Тестовая строка первой карточки',
  'Тестовая строка второй карточки',
  'Тестовая строка третьей карточки',
  'Тестовая строка четвёртой карточки',
  'Тестовая строка пятой карточки',
]

function CineLibraryHero() {
  return (
    <div className="cinelibrary-hero">
      <CineLibraryWordmark variant={getTypographyVariant(16)} />
      <p className="cinelibrary-tagline">Ваша личная история кино</p>
    </div>
  )
}

function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [movies, setMovies] = useState<MovieView[]>([])
  const [knownMovies, setKnownMovies] = useState<MovieView[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<LibraryFilter>('all')
  const [genre, setGenre] = useState('')
  const [sort, setSort] = useState<LibrarySort>('release_desc')
  const [knownGenres, setKnownGenres] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedMovie, setSelectedMovie] = useState<MovieView | null>(null)
  const [selectedPerson, setSelectedPerson] = useState<MovieCredit | null>(null)
  const [personDetails, setPersonDetails] = useState<PersonRecord | null>(null)
  const [isPersonLoading, setIsPersonLoading] = useState(false)
  const [personError, setPersonError] = useState('')
  const [tasteTags, setTasteTags] = useState<TasteTagDefinition[]>([])
  const [isMovieEditing, setIsMovieEditing] = useState(false)
  const [draftPersonalRating, setDraftPersonalRating] = useState<number | null>(null)
  const [draftTagCodes, setDraftTagCodes] = useState<string[]>([])
  const [draftComment, setDraftComment] = useState('')
  const [filmographyPreview, setFilmographyPreview] =
    useState<FilmographyPreview | null>(null)
  const [requestedMovieIds, setRequestedMovieIds] = useState<Set<number>>(
    new Set(),
  )
  const [requestingMovieId, setRequestingMovieId] = useState<number | null>(null)
  const [enlargedImage, setEnlargedImage] = useState<{
    src: string
    alt: string
  } | null>(null)
  const [isRecommendationOpen, setIsRecommendationOpen] = useState(false)
  const [configuratorStep, setConfiguratorStep] = useState(0)
  const [configuratorSelections, setConfiguratorSelections] = useState<boolean[]>(
    () => configuratorCards.map(() => false),
  )
  const [isConfiguratorSummary, setIsConfiguratorSummary] = useState(false)
  const [isEditingConfiguratorStep, setIsEditingConfiguratorStep] =
    useState(false)
  const [configuratorNotice, setConfiguratorNotice] = useState('')
  const movieCloseButtonRef = useRef<HTMLButtonElement>(null)
  const movieTriggerRef = useRef<HTMLElement | null>(null)
  const previewCloseTimerRef = useRef<number | null>(null)
  const selectedMovieId = selectedMovie?.id

  const closeMovie = () => {
    setSelectedPerson(null)
    setSelectedMovie(null)
    setIsMovieEditing(false)
    setDraftPersonalRating(null)
    setDraftTagCodes([])
    setDraftComment('')
  }

  const openMovie = (movie: MovieView) => {
    movieTriggerRef.current = document.activeElement as HTMLElement | null
    setIsMovieEditing(false)
    setSelectedMovie(movie)
  }

  const closePerson = () => {
    if (previewCloseTimerRef.current !== null) {
      window.clearTimeout(previewCloseTimerRef.current)
      previewCloseTimerRef.current = null
    }
    setFilmographyPreview(null)
    setSelectedPerson(null)
    setPersonDetails(null)
    setIsPersonLoading(false)
    setPersonError('')
  }

  const openPerson = (person: MovieCredit) => {
    setFilmographyPreview(null)
    setPersonDetails(null)
    setIsPersonLoading(person.personId !== null)
    setPersonError(
      person.personId === null
        ? 'Карточка пока не связана с базой людей.'
        : '',
    )
    setSelectedPerson(person)
  }

  const showFilmographyPreview = (
    element: HTMLElement,
    credit: PersonFilmographyItem,
    localMovie: MovieView | null,
  ) => {
    if (previewCloseTimerRef.current !== null) {
      window.clearTimeout(previewCloseTimerRef.current)
      previewCloseTimerRef.current = null
    }
    const bounds = element.getBoundingClientRect()
    const width = Math.min(728, window.innerWidth - 32)
    const estimatedHeight = 312
    const left = Math.min(
      Math.max(16, bounds.left),
      window.innerWidth - width - 16,
    )
    const top =
      bounds.top >= estimatedHeight + 26
        ? bounds.top - estimatedHeight - 10
        : Math.min(
            bounds.bottom + 10,
            window.innerHeight - estimatedHeight - 16,
          )
    setFilmographyPreview({
      title: localMovie?.title ?? credit.title,
      originalTitle: localMovie?.originalTitle ?? credit.originalTitle,
      year: localMovie?.year ?? credit.releaseYear,
      poster: localMovie?.poster ?? credit.posterUrl,
      genres: localMovie?.genres ?? [],
      rating: localMovie?.rating ?? credit.voteAverage,
      personalRating: localMovie?.personalRating ?? null,
      overview: localMovie?.overview ?? '',
      role: credit.character || credit.job,
      inLibrary: localMovie !== null,
      availability: localMovie?.availability ?? 'missing',
      tmdbMovieId: credit.tmdbMovieId,
      localMovieId: localMovie?.id ?? null,
      top,
      left,
      width,
    })
  }

  const scheduleFilmographyPreviewClose = () => {
    previewCloseTimerRef.current = window.setTimeout(() => {
      setFilmographyPreview(null)
      previewCloseTimerRef.current = null
    }, 180)
  }

  const keepFilmographyPreviewOpen = () => {
    if (previewCloseTimerRef.current !== null) {
      window.clearTimeout(previewCloseTimerRef.current)
      previewCloseTimerRef.current = null
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setIsLoading(true)
      setError('')
      loadMovies(search, filter, { genre, sort }, controller.signal)
        .then((loadedMovies) => {
          setMovies(loadedMovies)
          setKnownMovies((currentMovies) => {
            const movieById = new Map(
              currentMovies.map((movie) => [movie.id, movie]),
            )
            loadedMovies.forEach((movie) => movieById.set(movie.id, movie))
            return Array.from(movieById.values())
          })
          setKnownGenres((currentGenres) =>
            Array.from(
              new Set([
                ...currentGenres,
                ...loadedMovies.flatMap((movie) => movie.genres),
              ]),
            ).sort((left, right) => left.localeCompare(right, 'ru')),
          )
        })
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
  }, [search, filter, genre, sort])

  useEffect(() => {
    const controller = new AbortController()
    loadGenres(controller.signal)
      .then((genres) =>
        setKnownGenres(
          genres.sort((left, right) => left.localeCompare(right, 'ru')),
        ),
      )
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadTasteTags(controller.signal)
      .then(setTasteTags)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
        setError('Не удалось загрузить теги впечатлений.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadDownloadRequests(controller.signal)
      .then((requests) => {
        setRequestedMovieIds(
          new Set(requests.map((request) => request.tmdbMovieId)),
        )
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
        setError('Не удалось загрузить запросы на загрузку.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    document.body.style.overflow = selectedMovie || isRecommendationOpen
      ? 'hidden'
      : ''

    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedMovie, isRecommendationOpen])

  useEffect(() => {
    if (selectedMovieId === undefined) return

    movieCloseButtonRef.current?.focus()

    return () => {
      movieTriggerRef.current?.focus()
      movieTriggerRef.current = null
    }
  }, [selectedMovieId])

  useEffect(() => {
    if (!selectedPerson) return
    if (selectedPerson.personId === null) return

    const controller = new AbortController()
    loadPerson(selectedPerson.personId, controller.signal)
      .then(setPersonDetails)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === 'AbortError') {
          return
        }
        setPersonError('Не удалось загрузить карточку человека.')
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsPersonLoading(false)
      })

    return () => controller.abort()
  }, [selectedPerson])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (enlargedImage) {
          setEnlargedImage(null)
        } else if (selectedPerson) {
          closePerson()
        } else if (isMovieEditing) {
          setIsMovieEditing(false)
          setDraftPersonalRating(null)
          setDraftTagCodes([])
          setDraftComment('')
        } else if (selectedMovie) {
          closeMovie()
        } else if (isRecommendationOpen) {
          setIsRecommendationOpen(false)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [
    selectedMovie,
    selectedPerson,
    isMovieEditing,
    enlargedImage,
    isRecommendationOpen,
  ])

  const director = selectedMovie?.director ?? null
  const actors = selectedMovie?.actors ?? []

  const finishConfiguratorCard = () => {
    setConfiguratorNotice('')
    if (isEditingConfiguratorStep) {
      setIsEditingConfiguratorStep(false)
      setIsConfiguratorSummary(true)
      return
    }
    if (configuratorStep === configuratorCards.length - 1) {
      setIsConfiguratorSummary(true)
      return
    }
    setConfiguratorStep((currentStep) => currentStep + 1)
  }

  const skipConfiguratorCard = () => {
    setConfiguratorSelections((currentSelections) =>
      currentSelections.map((isSelected, index) =>
        index === configuratorStep ? false : isSelected,
      ),
    )
    finishConfiguratorCard()
  }

  const editConfiguratorCard = (step: number) => {
    setConfiguratorStep(step)
    setIsEditingConfiguratorStep(true)
    setIsConfiguratorSummary(false)
    setConfiguratorNotice('')
  }

  const applyUserData = async (
    movie: MovieView,
    changes: MovieUserDataUpdate,
  ) => {
    try {
      const updatedMovie = await saveUserData(movie.id, changes)
      setMovies((currentMovies) =>
        currentMovies.map((item) =>
          item.id === updatedMovie.id ? updatedMovie : item,
        ).filter((item) => {
          if (filter === 'high-rated') return (item.personalRating ?? 0) >= 4
          if (filter === 'rewatch') {
            return item.feedbackTagCodes.includes('outcome:rewatch')
          }
          if (filter === 'disliked') {
            return item.personalRating !== null && item.personalRating <= 2
          }
          if (filter === 'unrated') return item.personalRating === null
          if (filter === 'untagged') return item.feedbackTagCodes.length === 0
          return true
        }),
      )
      setSelectedMovie(updatedMovie)
      setKnownMovies((currentMovies) => {
        const exists = currentMovies.some((item) => item.id === updatedMovie.id)
        return exists
          ? currentMovies.map((item) =>
              item.id === updatedMovie.id ? updatedMovie : item,
            )
          : [...currentMovies, updatedMovie]
      })
      setError('')
      return true
    } catch {
      setError('Не удалось сохранить личные отметки.')
      return false
    }
  }

  const startMovieEditing = () => {
    if (!selectedMovie) return
    setDraftPersonalRating(selectedMovie.personalRating)
    setDraftTagCodes(selectedMovie.feedbackTagCodes)
    setDraftComment(selectedMovie.comment)
    setIsMovieEditing(true)
  }

  const cancelMovieEditing = () => {
    setIsMovieEditing(false)
    setDraftPersonalRating(null)
    setDraftTagCodes([])
    setDraftComment('')
  }

  const saveMovieEditing = async () => {
    if (!selectedMovie) return
    const saved = await applyUserData(selectedMovie, {
      personalRating: draftPersonalRating,
      tagCodes: draftTagCodes,
      comment: draftComment.trim(),
    })
    if (saved) cancelMovieEditing()
  }

  const submitDownloadRequest = async (preview: FilmographyPreview) => {
    if (
      requestedMovieIds.has(preview.tmdbMovieId) ||
      requestingMovieId === preview.tmdbMovieId
    ) {
      return
    }
    setRequestingMovieId(preview.tmdbMovieId)
    try {
      const request = await requestMovieDownload({
        tmdbMovieId: preview.tmdbMovieId,
        localMovieId: preview.localMovieId,
        title: preview.title,
      })
      setRequestedMovieIds((currentIds) => {
        const nextIds = new Set(currentIds)
        nextIds.add(request.tmdbMovieId)
        return nextIds
      })
      setError('')
    } catch {
      setError('Не удалось отправить запрос на загрузку.')
    } finally {
      setRequestingMovieId(null)
    }
  }

  const toggleTasteTag = (tag: TasteTagDefinition) => {
    setDraftTagCodes((currentCodes) => {
      if (currentCodes.includes(tag.code)) {
        return currentCodes.filter((code) => code !== tag.code)
      }
      let nextCodes = [...currentCodes]
      if (tag.category === 'outcome') {
        nextCodes = nextCodes.filter((code) => !code.startsWith('outcome:'))
      }
      if (tag.category === 'strength' || tag.category === 'weakness') {
        const aspect = tag.code.split(':')[1]
        const opposite = tag.category === 'strength' ? 'weakness' : 'strength'
        nextCodes = nextCodes.filter((code) => code !== `${opposite}:${aspect}`)
      }
      return [...nextCodes, tag.code]
    })
  }

  const selectMenuItem = (selectedFilter: LibraryFilter) => {
    setFilter(selectedFilter)
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
          {menuItems.map((item) => (
            <button
              className={`nav-item ${filter === item.filter ? 'active' : ''}`}
              key={item.label}
              onClick={() => selectMenuItem(item.filter)}
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
          <CineLibraryHero />

          <button
            className="add-button"
            onClick={() => setIsRecommendationOpen(true)}
          >
            Подобрать фильмы
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
          </div>

          <div className="library-controls">
            <label className="search-field">
              <span className="visually-hidden">Поиск фильмов</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Название, актёр или режиссёр"
              />
            </label>

            <select
              value={genre}
              onChange={(event) => setGenre(event.target.value)}
              aria-label="Фильтр по жанру"
            >
              <option value="">Все жанры</option>
              {knownGenres.map((item) => (
                <option value={item} key={item}>{item}</option>
              ))}
            </select>

            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as LibrarySort)}
              aria-label="Сортировка фильмов"
            >
              <option value="release_desc">Сначала новые</option>
              <option value="release_asc">Сначала старые</option>
              <option value="title_asc">По названию</option>
              <option value="rating_desc">По моей оценке</option>
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
                  onClick={() => openMovie(movie)}
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

      {isRecommendationOpen && (
        <div
          className="recommendation-overlay"
          onClick={() => setIsRecommendationOpen(false)}
        >
          <section
            className="recommendation-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="recommendation-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="movie-modal-close"
              onClick={() => setIsRecommendationOpen(false)}
              aria-label="Закрыть подбор фильмов"
            >
              ×
            </button>

            <header className="recommendation-header">
              <span className="eyebrow">ИНТЕЛЛЕКТУАЛЬНЫЙ ПОДБОР</span>
              <h2 id="recommendation-title">
                {isConfiguratorSummary ? 'Сводка запроса' : 'Подбор фильмов'}
              </h2>
              <p>
                {isConfiguratorSummary
                  ? 'Проверьте ответы и при необходимости вернитесь к нужной карточке.'
                  : `Карточка ${configuratorStep + 1} из ${configuratorCards.length}`}
              </p>
            </header>

            {isConfiguratorSummary ? (
              <section className="configurator-summary">
                {configuratorCards.map((text, index) => (
                  <article key={text}>
                    <div>
                      <span>Карточка {index + 1}</span>
                      <strong>{text}</strong>
                      <small>
                        {configuratorSelections[index] ? 'Выбрано' : 'Пропущено'}
                      </small>
                    </div>
                    <button
                      type="button"
                      onClick={() => editConfiguratorCard(index)}
                    >
                      Изменить
                    </button>
                  </article>
                ))}

                {configuratorNotice && (
                  <p className="configurator-notice">{configuratorNotice}</p>
                )}

                <div className="configurator-actions">
                  <button
                    type="button"
                    className="configurator-secondary"
                    onClick={() => {
                      setConfiguratorSelections(configuratorCards.map(() => false))
                      setConfiguratorStep(0)
                      setIsConfiguratorSummary(false)
                      setConfiguratorNotice('')
                    }}
                  >
                    Пройти заново
                  </button>
                  <button
                    type="button"
                    className="configurator-primary"
                    onClick={() =>
                      setConfiguratorNotice(
                        'Каркас работает. Подключение агента будет следующим этапом.',
                      )
                    }
                  >
                    Получить рекомендации
                  </button>
                </div>
              </section>
            ) : (
              <section className="configurator-card">
                <div className="configurator-progress" aria-hidden="true">
                  <span
                    style={{
                      width: `${((configuratorStep + 1) / configuratorCards.length) * 100}%`,
                    }}
                  />
                </div>

                <button
                  type="button"
                  className={
                    configuratorSelections[configuratorStep]
                      ? 'configurator-option is-selected'
                      : 'configurator-option'
                  }
                  aria-pressed={configuratorSelections[configuratorStep]}
                  onClick={() => {
                    setConfiguratorSelections((currentSelections) =>
                      currentSelections.map((isSelected, index) =>
                        index === configuratorStep ? !isSelected : isSelected,
                      ),
                    )
                    setConfiguratorNotice('')
                  }}
                >
                  <span>{configuratorCards[configuratorStep]}</span>
                  <strong>
                    {configuratorSelections[configuratorStep] ? 'Выбрано' : 'Выбрать'}
                  </strong>
                </button>

                <div className="configurator-actions">
                  <button
                    type="button"
                    className="configurator-secondary"
                    disabled={!isEditingConfiguratorStep && configuratorStep === 0}
                    onClick={() => {
                      if (isEditingConfiguratorStep) {
                        setIsEditingConfiguratorStep(false)
                        setIsConfiguratorSummary(true)
                      } else {
                        setConfiguratorStep((currentStep) => currentStep - 1)
                      }
                    }}
                  >
                    {isEditingConfiguratorStep ? 'К сводке' : 'Назад'}
                  </button>
                  <button
                    type="button"
                    className="configurator-secondary"
                    onClick={skipConfiguratorCard}
                  >
                    Пропустить
                  </button>
                  <button
                    type="button"
                    className="configurator-primary"
                    onClick={finishConfiguratorCard}
                  >
                    {isEditingConfiguratorStep
                      ? 'Сохранить'
                      : configuratorStep === configuratorCards.length - 1
                        ? 'К сводке'
                        : 'Далее'}
                  </button>
                </div>
              </section>
            )}
          </section>
        </div>
      )}

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
              ref={movieCloseButtonRef}
              className="movie-modal-close"
              onClick={closeMovie}
              aria-label="Закрыть карточку"
            >
              ×
            </button>

            <div className="movie-modal-top">
              <div className="movie-modal-poster-wrap">
                {selectedMovie.poster ? (
                  <button
                    type="button"
                    className="image-zoom-button"
                    onClick={() =>
                      setEnlargedImage({
                        src: selectedMovie.poster as string,
                        alt: selectedMovie.title,
                      })
                    }
                    aria-label={`Увеличить постер фильма ${selectedMovie.title}`}
                  >
                    <img
                      className="movie-modal-poster"
                      src={selectedMovie.poster}
                      alt={selectedMovie.title}
                    />
                  </button>
                ) : (
                  <div className="movie-modal-poster movie-modal-poster-fallback">
                    Постер отсутствует
                  </div>
                )}
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
                  <span>
                    {(selectedMovie.genres.length > 0
                      ? selectedMovie.genres
                      : [selectedMovie.genre]
                    ).join(', ')}
                  </span>
                </div>

                {selectedMovie.rating !== null && (
                  <div className="movie-modal-rating">
                    <span className="movie-modal-rating-star">★</span>
                    <strong>{selectedMovie.rating.toFixed(1)}</strong>
                    <small>IMDb</small>
                  </div>
                )}

                <div className="movie-modal-statuses">
                  <div
                    className={`movie-modal-status status-${selectedMovie.availability}`}
                  >
                    <span className="availability-dot" />
                    {availabilityLabels[selectedMovie.availability]}
                  </div>

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
            </div>

            <div className="movie-modal-body">
              <section className="movie-modal-section movie-description">
                <h3>О фильме</h3>
                <p>
                  {selectedMovie.overview || 'Описание пока отсутствует.'}
                </p>
              </section>

              <div className="movie-modal-people">
                <section className="movie-modal-section">
                  <h3>Режиссёр</h3>

                  {director ? (
                    <button
                      type="button"
                      className="movie-person-link"
                      onClick={() => openPerson(director)}
                    >
                      {director.displayName}
                    </button>
                  ) : (
                    <p>Информация о режиссёре отсутствует.</p>
                  )}
                </section>

                <section className="movie-modal-section">
                  <h3>В ролях</h3>

                  {actors.length > 0 ? (
                    <div className="movie-people-list">
                      {actors.map((actor) => (
                        <button
                          type="button"
                          className="movie-person-link"
                          key={actor.id}
                          onClick={() => openPerson(actor)}
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

              <section className="movie-modal-section personal-section">
                <div className="personal-section-header">
                  <h3>Мои впечатления</h3>
                  {!isMovieEditing && (
                    <button type="button" onClick={startMovieEditing}>
                      Редактировать
                    </button>
                  )}
                </div>

                {!isMovieEditing ? (
                  <div className="personal-view">
                    <div className="personal-rating-block">
                      <span>Моя оценка</span>
                      <div
                        className="star-rating star-rating-static"
                        aria-label={
                          selectedMovie.personalRating === null
                            ? 'Без оценки'
                            : `${selectedMovie.personalRating} из 5`
                        }
                      >
                        {[1, 2, 3, 4, 5].map((rating) => (
                          <span
                            className={
                              selectedMovie.personalRating !== null &&
                              rating <= selectedMovie.personalRating
                                ? 'star is-active'
                                : 'star'
                            }
                            aria-hidden="true"
                            key={rating}
                          >
                            ★
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="taste-feedback-header">
                      <span>Теги впечатлений</span>
                    </div>
                    {selectedMovie.feedbackTags.length > 0 ? (
                      <div className="movie-detail-tags">
                        {selectedMovie.feedbackTags.map((tag) => (
                          <span className="movie-detail-tag" key={tag}>{tag}</span>
                        ))}
                      </div>
                    ) : (
                      <p>Впечатления пока не добавлены.</p>
                    )}

                    <div className="movie-comment">
                      <span>Мой комментарий</span>
                      <p>{selectedMovie.comment || 'Комментарий пока не добавлен.'}</p>
                    </div>
                  </div>
                ) : (
                  <div className="taste-tag-editor">
                    <div className="rating-editor">
                      <span>Моя оценка</span>
                      <div className="star-rating" role="group" aria-label="Моя оценка">
                        {[1, 2, 3, 4, 5].map((rating) => (
                          <button
                            type="button"
                            className={
                              draftPersonalRating !== null && rating <= draftPersonalRating
                                ? 'star is-active'
                                : 'star'
                            }
                            aria-label={`Поставить ${rating} из 5`}
                            aria-pressed={draftPersonalRating === rating}
                            key={rating}
                            onClick={() => setDraftPersonalRating(rating)}
                          >
                            ★
                          </button>
                        ))}
                      </div>
                      {draftPersonalRating !== null && (
                        <button
                          type="button"
                          className="rating-clear"
                          onClick={() => setDraftPersonalRating(null)}
                        >
                          Сбросить оценку
                        </button>
                      )}
                    </div>

                    <p>
                      Выберите несколько точных впечатлений — заполнять все группы
                      необязательно.
                    </p>

                    {[
                      ['viewing', 'Как смотрелось'],
                      ['emotion', 'Что почувствовали'],
                    ].map(([category, title]) => (
                      <div className="taste-tag-group" key={category}>
                        <h4>{title}</h4>
                        <div className="taste-tag-options">
                          {tasteTags
                            .filter((tag) => tag.category === category)
                            .map((tag) => (
                              <button
                                type="button"
                                className={
                                  draftTagCodes.includes(tag.code)
                                    ? 'taste-tag-option is-selected'
                                    : 'taste-tag-option'
                                }
                                aria-pressed={draftTagCodes.includes(tag.code)}
                                key={tag.code}
                                onClick={() => toggleTasteTag(tag)}
                              >
                                {tag.label}
                              </button>
                            ))}
                        </div>
                      </div>
                    ))}

                    <details className="taste-aspects">
                      <summary>Что именно понравилось или не понравилось?</summary>
                      {[
                        ['strength', 'Понравилось'],
                        ['weakness', 'Не понравилось'],
                      ].map(([category, title]) => (
                        <div className="taste-tag-group" key={category}>
                          <h4>{title}</h4>
                          <div className="taste-tag-options">
                            {tasteTags
                              .filter((tag) => tag.category === category)
                              .map((tag) => (
                                <button
                                  type="button"
                                  className={
                                    draftTagCodes.includes(tag.code)
                                      ? 'taste-tag-option is-selected'
                                      : 'taste-tag-option'
                                  }
                                  aria-pressed={draftTagCodes.includes(tag.code)}
                                  key={tag.code}
                                  onClick={() => toggleTasteTag(tag)}
                                >
                                  {tag.label.split(' — ')[0]}
                                </button>
                              ))}
                          </div>
                        </div>
                      ))}
                    </details>

                    <div className="taste-tag-group">
                      <h4>Итог</h4>
                      <div className="taste-tag-options">
                        {tasteTags
                          .filter((tag) => tag.category === 'outcome')
                          .map((tag) => (
                            <button
                              type="button"
                              className={
                                draftTagCodes.includes(tag.code)
                                  ? 'taste-tag-option is-selected'
                                  : 'taste-tag-option'
                              }
                              aria-pressed={draftTagCodes.includes(tag.code)}
                              key={tag.code}
                              onClick={() => toggleTasteTag(tag)}
                            >
                              {tag.label}
                            </button>
                          ))}
                      </div>
                    </div>

                    <label className="comment-editor">
                      <span>Мой комментарий</span>
                      <textarea
                        value={draftComment}
                        maxLength={4000}
                        rows={5}
                        onChange={(event) => setDraftComment(event.target.value)}
                        placeholder="Что хочется запомнить об этом фильме?"
                      />
                    </label>

                    <div className="taste-tag-editor-actions">
                      <button
                        type="button"
                        className="taste-tag-save"
                        onClick={saveMovieEditing}
                      >
                        Сохранить
                      </button>
                      <button
                        type="button"
                        onClick={cancelMovieEditing}
                      >
                        Отмена
                      </button>
                    </div>
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
          onClick={closePerson}
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
              onClick={closePerson}
              aria-label="Закрыть карточку"
            >
              ×
            </button>

            {isPersonLoading && (
              <p className="person-modal-message">Загружаем карточку…</p>
            )}

            {personError && (
              <p className="person-modal-message person-modal-error">
                {personError}
              </p>
            )}

            {personDetails && (
              <>
                <div className="person-modal-hero">
                  {personDetails.profileUrl ? (
                    <button
                      type="button"
                      className="image-zoom-button"
                      onClick={() =>
                        setEnlargedImage({
                          src: personDetails.profileUrl as string,
                          alt: personDetails.displayName,
                        })
                      }
                      aria-label={`Увеличить фото ${personDetails.displayName}`}
                    >
                      <img
                        className="person-profile-photo"
                        src={personDetails.profileUrl}
                        alt={personDetails.displayName}
                      />
                    </button>
                  ) : (
                    <div className="person-profile-photo person-photo-fallback">
                      Фото отсутствует
                    </div>
                  )}

                  <div className="person-modal-summary">
                    <div className="eyebrow">КАРТОЧКА ЧЕЛОВЕКА</div>
                    <h2>{personDetails.displayName}</h2>
                    {personDetails.displayName !== personDetails.name && (
                      <p className="person-original-name">{personDetails.name}</p>
                    )}
                    {personDetails.knownForDepartment && (
                      <p>{personDetails.knownForDepartment}</p>
                    )}
                    {(personDetails.birthday || personDetails.deathday) && (
                      <p>
                        {personDetails.birthday || 'Дата рождения неизвестна'}
                        {personDetails.deathday
                          ? ` — ${personDetails.deathday}`
                          : ''}
                      </p>
                    )}
                    {personDetails.placeOfBirth && (
                      <p>{personDetails.placeOfBirth}</p>
                    )}
                    <small>
                      Обновлено:{' '}
                      {new Date(personDetails.lastRefreshedAt).toLocaleDateString(
                        'ru-RU',
                      )}
                    </small>
                  </div>
                </div>

                {personDetails.biography && (
                  <section className="person-modal-section">
                    <h3>Биография</h3>
                    <p>{personDetails.biography}</p>
                  </section>
                )}

                <section className="person-modal-section">
                  <h3>Фильмография</h3>
                  <div className="person-filmography">
                    {personDetails.filmography.map((credit, index) => {
                      const localMovie = credit.localMovieId
                        ? knownMovies.find(
                            (movie) => movie.id === credit.localMovieId,
                          )
                        : null
                      const content = (
                        <>
                          {credit.posterUrl ? (
                            <img src={credit.posterUrl} alt="" />
                          ) : (
                            <div className="filmography-poster-fallback">Нет постера</div>
                          )}
                          <span className="filmography-info">
                            <strong>{credit.title}</strong>
                            <small>
                              {credit.releaseYear || 'Год неизвестен'}
                              {(credit.character || credit.job) &&
                                ` · ${credit.character || credit.job}`}
                            </small>
                            {credit.inLibrary && <em>В моей библиотеке</em>}
                          </span>
                        </>
                      )

                      return localMovie ? (
                        <button
                          type="button"
                          className="filmography-item filmography-item-link"
                          key={`${credit.tmdbMovieId}-${index}`}
                          onMouseEnter={(event) =>
                            showFilmographyPreview(
                              event.currentTarget,
                              credit,
                              localMovie,
                            )
                          }
                          onMouseLeave={scheduleFilmographyPreviewClose}
                          onFocus={(event) =>
                            showFilmographyPreview(
                              event.currentTarget,
                              credit,
                              localMovie,
                            )
                          }
                          onBlur={() => setFilmographyPreview(null)}
                          onClick={() => {
                            setFilmographyPreview(null)
                            closePerson()
                            setIsMovieEditing(false)
                            setDraftPersonalRating(null)
                            setDraftTagCodes([])
                            setDraftComment('')
                            setSelectedMovie(localMovie)
                          }}
                        >
                          {content}
                        </button>
                      ) : (
                        <div
                          className="filmography-item"
                          key={`${credit.tmdbMovieId}-${index}`}
                          onMouseEnter={(event) =>
                            showFilmographyPreview(event.currentTarget, credit, null)
                          }
                          onMouseLeave={scheduleFilmographyPreviewClose}
                        >
                          {content}
                        </div>
                      )
                    })}
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      )}

      {filmographyPreview && (
        <div
          className="filmography-movie-preview"
          style={{
            top: filmographyPreview.top,
            left: filmographyPreview.left,
            width: filmographyPreview.width,
          }}
          onMouseEnter={keepFilmographyPreviewOpen}
          onMouseLeave={scheduleFilmographyPreviewClose}
        >
          {filmographyPreview.poster ? (
            <button
              type="button"
              className="image-zoom-button filmography-preview-image-button"
              onClick={() =>
                setEnlargedImage({
                  src: filmographyPreview.poster as string,
                  alt: filmographyPreview.title,
                })
              }
              aria-label={`Увеличить постер фильма ${filmographyPreview.title}`}
            >
              <img
                className="filmography-preview-poster"
                src={filmographyPreview.poster}
                alt={filmographyPreview.title}
              />
            </button>
          ) : (
            <span className="filmography-preview-poster filmography-preview-poster-fallback">
              Нет постера
            </span>
          )}
          <span className="filmography-preview-body">
            <strong>{filmographyPreview.title}</strong>
            {filmographyPreview.originalTitle !== filmographyPreview.title && (
              <small>{filmographyPreview.originalTitle}</small>
            )}
            <span className="filmography-preview-meta">
              {filmographyPreview.year || 'Год неизвестен'}
              {filmographyPreview.genres.length > 0 &&
                ` · ${filmographyPreview.genres.join(', ')}`}
              {filmographyPreview.role && ` · ${filmographyPreview.role}`}
            </span>
            <span className="filmography-preview-ratings">
              {filmographyPreview.rating !== null && (
                <em>TMDB {filmographyPreview.rating.toFixed(1)}</em>
              )}
              {filmographyPreview.personalRating !== null && (
                <em>Моя оценка ★ {filmographyPreview.personalRating}</em>
              )}
            </span>
            <span className="filmography-preview-overview">
              {filmographyPreview.overview ||
                'Сокращённая запись фильмографии из TMDB.'}
            </span>
            <span className="filmography-preview-footer">
              <span
                className={
                  filmographyPreview.inLibrary
                    ? 'filmography-preview-source is-local'
                    : 'filmography-preview-source'
                }
              >
                {filmographyPreview.inLibrary
                  ? 'В моей библиотеке'
                  : 'Данные TMDB'}
              </span>
              {filmographyPreview.availability === 'missing' &&
                !requestedMovieIds.has(filmographyPreview.tmdbMovieId) && (
                <button
                  type="button"
                  className="filmography-preview-download"
                  disabled={requestingMovieId === filmographyPreview.tmdbMovieId}
                  onClick={() => submitDownloadRequest(filmographyPreview)}
                >
                  {requestingMovieId === filmographyPreview.tmdbMovieId
                    ? 'Отправляем…'
                    : 'Запросить загрузку'}
                </button>
              )}
              {requestedMovieIds.has(filmographyPreview.tmdbMovieId) && (
                <span className="filmography-preview-requested">
                  Запрос отправлен
                </span>
              )}
              {filmographyPreview.availability === 'downloading' && (
                <span className="filmography-preview-downloading">
                  Скачивается
                </span>
              )}
            </span>
          </span>
        </div>
      )}

      {enlargedImage && (
        <div
          className="image-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={`Увеличенное изображение: ${enlargedImage.alt}`}
          onClick={() => setEnlargedImage(null)}
        >
          <button
            type="button"
            className="image-lightbox-close"
            onClick={() => setEnlargedImage(null)}
            aria-label="Закрыть увеличенное изображение"
          >
            ×
          </button>
          <img
            src={enlargedImage.src}
            alt={enlargedImage.alt}
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

export default App
