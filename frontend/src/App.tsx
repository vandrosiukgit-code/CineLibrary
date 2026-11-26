
import { useEffect, useRef, useState } from 'react'
import './App.css'
import { RecommendationResults } from './components/RecommendationResults'
import {
  loadDownloadRequests,
  loadAPICredentials,
  findTelegramChats,
  loadGenres,
  loadTasteTags,
  loadTelegramSettings,
  loadMovies,
  requestMoviesByTmdb,
  saveUserData,
  saveTelegramSettings,
  saveAPICredentials,
  testTelegramSettings,
  type LibraryFilter,
  type LibrarySort,
  type MovieView,
  type TasteTagDefinition,
  type TelegramChat,
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
  cancelRecommendationJob,
  loadRecommendationJob,
  startRecommendationJob,
  type RecommendationJobLog,
  type RecommendationResponse,
} from './data/recommendationApi'
import {
  cancelLibraryImport,
  loadLibraryImport,
  startCandidateLibraryImport,
  startLibraryImport,
  getMediaSyncSettings,
  browseMediaFolders,
  saveMediaSyncSettings,
  runMediaSync,
  type MediaFolders,
  type LibraryImportItem,
  type LibraryImportLog,
} from './data/librarianApi'
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
  top: number | undefined
  bottom: number | undefined
  maxHeight: number
  left: number
  width: number
}

type ReferenceRelation = 'similar' | 'avoid'
type PreferenceRelation = 'prefer' | 'require' | 'exclude'

interface ConfiguratorSelection<Relation extends string> {
  id: string
  label: string
  relation: Relation
}

const availabilityLabels = {
  available: 'На диске',
  downloading: 'Скачивается',
  missing: 'Нет на диске',
}

const configuratorCards = [
  { id: 'wish', title: 'Пожелание', question: 'Какой фильм вы хотите посмотреть?' },
  {
    id: 'references',
    title: 'Фильмы-ориентиры',
    question: 'На какие просмотренные фильмы стоит ориентироваться?',
  },
  { id: 'genres', title: 'Жанры', question: 'Какие жанры учитывать?' },
  {
    id: 'constraints',
    title: 'Дополнительные ограничения',
    question: 'Есть ли дополнительные ограничения?',
  },
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
  const [isTelegramSettingsOpen, setIsTelegramSettingsOpen] = useState(false)
  const [isAPICredentialsOpen, setIsAPICredentialsOpen] = useState(false)
  const [replicateConfigured, setReplicateConfigured] = useState(false)
  const [tmdbConfigured, setTmdbConfigured] = useState(false)
  const [replicateApiToken, setReplicateApiToken] = useState('')
  const [tmdbReadAccessToken, setTmdbReadAccessToken] = useState('')
  const [apiCredentialsStatus, setApiCredentialsStatus] = useState('')
  const [isSavingAPICredentials, setIsSavingAPICredentials] = useState(false)
  const [telegramConfigured, setTelegramConfigured] = useState(false)
  const [telegramBotToken, setTelegramBotToken] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')
  const [telegramSettingsStatus, setTelegramSettingsStatus] = useState('')
  const [isSavingTelegramSettings, setIsSavingTelegramSettings] = useState(false)
  const [telegramChats, setTelegramChats] = useState<TelegramChat[]>([])
  const [isFindingTelegramChats, setIsFindingTelegramChats] = useState(false)
  const [movies, setMovies] = useState<MovieView[]>([])
  const [knownMovies, setKnownMovies] = useState<MovieView[]>([])
  const [search, setSearch] = useState('')
  const [filter] = useState<LibraryFilter>('all')
  const [genre, setGenre] = useState('')
  const [availability, setAvailability] = useState<AvailabilityStatus | ''>('')
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
  const [failedDownloadMovieId, setFailedDownloadMovieId] = useState<number | null>(null)
  const [enlargedImage, setEnlargedImage] = useState<{
    src: string
    alt: string
  } | null>(null)
  const [isRecommendationOpen, setIsRecommendationOpen] = useState(false)
  const [isLibraryImportOpen, setIsLibraryImportOpen] = useState(false)
  const [libraryImportText, setLibraryImportText] = useState('')
  const [libraryImportJobId, setLibraryImportJobId] = useState<string | null>(null)
  const [libraryImportLogs, setLibraryImportLogs] = useState<LibraryImportLog[]>([])
  const [libraryImportItems, setLibraryImportItems] = useState<LibraryImportItem[]>([])
  const [selectedImportCandidateIds, setSelectedImportCandidateIds] = useState<Set<number>>(
    new Set(),
  )
  const [activeCandidateImportIds, setActiveCandidateImportIds] = useState<Set<number>>(
    new Set(),
  )
  const [libraryImportError, setLibraryImportError] = useState('')
  const [isLibraryImportRunning, setIsLibraryImportRunning] = useState(false)
  const [isStoppingLibraryImport, setIsStoppingLibraryImport] = useState(false)
  const [catalogRevision, setCatalogRevision] = useState(0)
  const [configuratorStep, setConfiguratorStep] = useState(0)
  const [configuratorWish, setConfiguratorWish] = useState('')
  const [referenceSelections, setReferenceSelections] =
    useState<ConfiguratorSelection<ReferenceRelation>[]>([])
  const [genreSelections, setGenreSelections] =
    useState<ConfiguratorSelection<PreferenceRelation>[]>([])
  const [configuratorSearch, setConfiguratorSearch] = useState('')
  const [referenceGenre, setReferenceGenre] = useState('')
  const [referenceSort, setReferenceSort] = useState<LibrarySort>('release_desc')
  const [genreCandidate, setGenreCandidate] = useState('')
  const [genreCandidateRelation, setGenreCandidateRelation] =
    useState<PreferenceRelation>('prefer')
  const [configuratorConstraints, setConfiguratorConstraints] = useState({
    yearFrom: '',
    yearTo: '',
    maxRuntimeMinutes: '',
    country: '',
    certification: '',
    language: '',
  })
  const [isConfiguratorSummary, setIsConfiguratorSummary] = useState(false)
  const [isEditingConfiguratorStep, setIsEditingConfiguratorStep] =
    useState(false)
  const [configuratorNotice, setConfiguratorNotice] = useState('')
  const [recommendationCount, setRecommendationCount] = useState(5)
  const [recommendationResult, setRecommendationResult] =
    useState<RecommendationResponse | null>(null)
  const [isRecommending, setIsRecommending] = useState(false)
  const [recommendationJobId, setRecommendationJobId] = useState<string | null>(null)
  const [recommendationLogs, setRecommendationLogs] =
    useState<RecommendationJobLog[]>([])
  const [isStoppingRecommendation, setIsStoppingRecommendation] = useState(false)
  const [recommendationError, setRecommendationError] = useState('')
  const [isMediaSettingsOpen, setIsMediaSettingsOpen] = useState(false)
  const [mediaRoot, setMediaRoot] = useState('')
  const [mediaExclusions, setMediaExclusions] = useState<string[]>([])
  const [mediaPicker, setMediaPicker] = useState<'root' | 'exclude' | null>(null)
  const [mediaFolders, setMediaFolders] = useState<MediaFolders | null>(null)
  const [isMediaSettingsBusy, setIsMediaSettingsBusy] = useState(false)
  const [mediaSettingsMessage, setMediaSettingsMessage] = useState('')
  const [isMediaSyncing, setIsMediaSyncing] = useState(false)
  const [mediaSyncMessage, setMediaSyncMessage] = useState('')
  const [mediaPending, setMediaPending] = useState<string[]>([])
  const movieCloseButtonRef = useRef<HTMLButtonElement>(null)
  const movieTriggerRef = useRef<HTMLElement | null>(null)
  const previewTimerRef = useRef<number | null>(null)
  const selectedMovieId = selectedMovie?.id
  const selectedMovieTmdbId = selectedMovie?.tmdbId ?? null

  const openMediaSettings = async () => {
    setIsMediaSettingsOpen(true)
    setMediaSettingsMessage('')
    setIsMediaSettingsBusy(true)
    try {
      const settings = await getMediaSyncSettings()
      setMediaRoot(settings.root)
      setMediaExclusions(settings.excluded)
    } catch (error) {
      setMediaSettingsMessage(error instanceof Error ? error.message : 'Настройки недоступны.')
    } finally {
      setIsMediaSettingsBusy(false)
    }
  }

  const loadMediaFolders = async (path: string | null) => {
    setIsMediaSettingsBusy(true)
    setMediaSettingsMessage('')
    try {
      setMediaFolders(await browseMediaFolders(path))
    } catch (error) {
      setMediaSettingsMessage(error instanceof Error ? error.message : 'Папка недоступна.')
    } finally {
      setIsMediaSettingsBusy(false)
    }
  }

  const openMediaPicker = (mode: 'root' | 'exclude') => {
    setMediaPicker(mode)
    setMediaFolders(null)
    void loadMediaFolders(mode === 'exclude' ? mediaRoot : null)
  }

  const saveMediaSettings = async (root: string, excluded: string[]) => {
    setIsMediaSettingsBusy(true)
    try {
      const settings = await saveMediaSyncSettings({ root, excluded })
      setMediaRoot(settings.root)
      setMediaExclusions(settings.excluded)
      setMediaPicker(null)
      setMediaSettingsMessage('Настройки сохранены.')
    } catch (error) {
      setMediaSettingsMessage(error instanceof Error ? error.message : 'Не удалось сохранить настройки.')
    } finally {
      setIsMediaSettingsBusy(false)
    }
  }

  const syncMedia = async () => {
    setIsMediaSyncing(true)
    setMediaSyncMessage('Проверяем папку медиатеки…')
    setMediaPending([])
    try {
      const result = await runMediaSync()
      if (Object.keys(result.errors).length) {
        setMediaSyncMessage(`Не удалось проверить папки: ${Object.keys(result.errors).join(', ')}.`)
      } else {
        setMediaSyncMessage(`Связано копий: ${result.matched}. Проверка наличия повторяется каждые 15 минут.`)
        setMediaPending(result.pending)
      }
    } catch (error) {
      setMediaSyncMessage(error instanceof Error ? error.message : 'Синхронизация не завершилась.')
    } finally {
      setCatalogRevision((revision) => revision + 1)
      setIsMediaSyncing(false)
    }
  }

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
    if (previewTimerRef.current !== null) {
      window.clearTimeout(previewTimerRef.current)
      previewTimerRef.current = null
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
    keepFilmographyPreviewOpen()
    const bounds = element.getBoundingClientRect()
    const width = Math.min(728, window.innerWidth - 32)
    const left = Math.min(
      Math.max(16, bounds.left),
      window.innerWidth - width - 16,
    )
    const spaceAbove = bounds.top - 16
    const spaceBelow = window.innerHeight - bounds.bottom - 16
    const showAbove = spaceAbove >= 312 || spaceAbove >= spaceBelow
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
      top: showAbove ? undefined : bounds.bottom,
      bottom: showAbove ? window.innerHeight - bounds.top : undefined,
      maxHeight: showAbove ? spaceAbove : spaceBelow,
      left,
      width,
    })
  }

  const hoverFilmographyItem = (
    element: HTMLElement,
    credit: PersonFilmographyItem,
    localMovie: MovieView | null,
  ) => {
    keepFilmographyPreviewOpen()
    if (!filmographyPreview) {
      showFilmographyPreview(element, credit, localMovie)
    } else if (filmographyPreview.tmdbMovieId !== credit.tmdbMovieId) {
      previewTimerRef.current = window.setTimeout(() => {
        showFilmographyPreview(element, credit, localMovie)
      }, 240)
    }
  }

  const scheduleFilmographyPreviewClose = () => {
    keepFilmographyPreviewOpen()
    previewTimerRef.current = window.setTimeout(() => {
      setFilmographyPreview(null)
      previewTimerRef.current = null
    }, 240)
  }

  const keepFilmographyPreviewOpen = () => {
    if (previewTimerRef.current !== null) {
      window.clearTimeout(previewTimerRef.current)
      previewTimerRef.current = null
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setIsLoading(true)
      setError('')
      loadMovies(search, filter, { genre, sort, availability }, controller.signal)
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
  }, [search, filter, genre, sort, availability, catalogRevision])

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
  }, [catalogRevision])

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
    if (!recommendationJobId) return
    let isActive = true

    const poll = async () => {
      try {
        const job = await loadRecommendationJob(recommendationJobId)
        if (!isActive) return
        setRecommendationLogs(job.logs)
        if (job.status === 'completed' && job.result) {
          setRecommendationResult(job.result)
          setIsRecommending(false)
          setIsStoppingRecommendation(false)
          setRecommendationJobId(null)
        } else if (job.status === 'failed') {
          setRecommendationError(job.error || 'Подбор завершился с ошибкой')
          setIsRecommending(false)
          setIsStoppingRecommendation(false)
          setRecommendationJobId(null)
        } else if (job.status === 'cancelled') {
          setRecommendationError('Подбор остановлен пользователем.')
          setIsRecommending(false)
          setIsStoppingRecommendation(false)
          setRecommendationJobId(null)
        }
      } catch (requestError) {
        if (!isActive) return
        setRecommendationError(
          requestError instanceof Error
            ? requestError.message
            : 'Не удалось получить состояние подбора',
        )
        setIsRecommending(false)
        setIsStoppingRecommendation(false)
        setRecommendationJobId(null)
      }
    }

    void poll()
    const timer = window.setInterval(() => void poll(), 1000)
    return () => {
      isActive = false
      window.clearInterval(timer)
    }
  }, [recommendationJobId])

  useEffect(() => {
    if (!libraryImportJobId) return
    let isActive = true

    const poll = async () => {
      try {
        const job = await loadLibraryImport(libraryImportJobId)
        if (!isActive) return
        setLibraryImportLogs(job.logs)
        if (job.status === 'completed') {
          setLibraryImportItems((currentItems) => [
            ...currentItems.filter((item) => !item.candidates.some(
              (candidate) => activeCandidateImportIds.has(candidate.tmdbId),
            )),
            ...(job.result?.items ?? []),
          ])
          setActiveCandidateImportIds(new Set())
          setIsLibraryImportRunning(false)
          setLibraryImportJobId(null)
          setCatalogRevision((revision) => revision + 1)
          return
        }
        if (job.status === 'failed' || job.status === 'cancelled') {
          setLibraryImportError(
            job.error || (job.status === 'cancelled' ? 'Добавление остановлено.' : 'Не удалось добавить фильмы.'),
          )
          setIsLibraryImportRunning(false)
          setIsStoppingLibraryImport(false)
          setLibraryImportJobId(null)
          return
        }
        window.setTimeout(poll, 1000)
      } catch (requestError) {
        if (!isActive) return
        setLibraryImportError(
          requestError instanceof Error ? requestError.message : 'Не удалось получить состояние импорта',
        )
        setIsLibraryImportRunning(false)
        setLibraryImportJobId(null)
      }
    }
    void poll()
    return () => { isActive = false }
  }, [libraryImportJobId, activeCandidateImportIds])

  useEffect(() => {
    document.body.style.overflow = selectedMovie || isRecommendationOpen || isLibraryImportOpen
      ? 'hidden'
      : ''

    return () => {
      document.body.style.overflow = ''
    }
  }, [selectedMovie, isRecommendationOpen, isLibraryImportOpen])

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
        } else if (isLibraryImportOpen) {
          setIsLibraryImportOpen(false)
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
    isLibraryImportOpen,
  ])

  const director = selectedMovie?.director ?? null
  const actors = selectedMovie?.actors ?? []
  const normalizedReferenceSearch = configuratorSearch
    .trim()
    .toLocaleLowerCase('ru')
  const referenceSearchTokens = normalizedReferenceSearch
    .split(/[^\p{L}\p{N}]+/u)
    .filter(Boolean)
  const referenceResults = normalizedReferenceSearch || referenceGenre
    ? knownMovies
      .filter((movie) => {
        const searchable = `${movie.title} ${movie.originalTitle} ${movie.people
          .map((person) => `${person.displayName} ${person.canonicalName}`)
          .join(' ')}`
          .toLocaleLowerCase('ru')
        return referenceSearchTokens.every((token) => searchable.includes(token))
          && (!referenceGenre || movie.genres.includes(referenceGenre))
      })
      .sort((left, right) => {
        if (referenceSort === 'release_asc') return left.year - right.year
        if (referenceSort === 'release_desc') return right.year - left.year
        if (referenceSort === 'rating_desc') {
          return (right.personalRating ?? -1) - (left.personalRating ?? -1)
        }
        return left.title.localeCompare(right.title, 'ru')
      })
      .slice(0, 12)
    : []

  const updateSelection = <Relation extends string,>(
    current: ConfiguratorSelection<Relation>[],
    id: string,
    label: string,
    relation: Relation | '',
  ) => {
    if (!relation) return current.filter((item) => item.id !== id)
    const existing = current.some((item) => item.id === id)
    return existing
      ? current.map((item) => item.id === id ? { ...item, relation } : item)
      : [...current, { id, label, relation }]
  }

  const getConfiguratorValues = (step: number): string[] => {
    if (step === 0) return configuratorWish.trim() ? [configuratorWish.trim()] : []
    if (step === 1) {
      return referenceSelections.map((item) =>
        `${item.relation === 'similar' ? 'Похожее на' : 'Не похожее на'}: ${item.label}`,
      )
    }
    if (step === 2) {
      const labels: Record<PreferenceRelation, string> = {
        prefer: 'Желательно',
        require: 'Обязательно',
        exclude: 'Исключить',
      }
      return genreSelections.map((item) => `${labels[item.relation]}: ${item.label}`)
    }
    return [
      configuratorConstraints.yearFrom
        ? `Год выпуска от: ${configuratorConstraints.yearFrom}`
        : '',
      configuratorConstraints.yearTo
        ? `Год выпуска до: ${configuratorConstraints.yearTo}`
        : '',
      configuratorConstraints.maxRuntimeMinutes
        ? `Продолжительность до: ${configuratorConstraints.maxRuntimeMinutes} минут`
        : '',
      configuratorConstraints.country
        ? `Страна: ${configuratorConstraints.country}`
        : '',
      configuratorConstraints.certification
        ? `Возрастной рейтинг: ${configuratorConstraints.certification}`
        : '',
      configuratorConstraints.language
        ? `Язык: ${configuratorConstraints.language}`
        : '',
    ].filter(Boolean)
  }

  const clearConfiguratorCard = (step: number) => {
    if (step === 0) setConfiguratorWish('')
    if (step === 1) setReferenceSelections([])
    if (step === 2) setGenreSelections([])
    if (step === 3) {
      setConfiguratorConstraints({
        yearFrom: '',
        yearTo: '',
        maxRuntimeMinutes: '',
        country: '',
        certification: '',
        language: '',
      })
    }
  }

  const finishConfiguratorCard = () => {
    setConfiguratorNotice('')
    setConfiguratorSearch('')
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
    clearConfiguratorCard(configuratorStep)
    finishConfiguratorCard()
  }

  const editConfiguratorCard = (step: number) => {
    setConfiguratorStep(step)
    setIsEditingConfiguratorStep(true)
    setIsConfiguratorSummary(false)
    setConfiguratorNotice('')
    setConfiguratorSearch('')
  }

  const submitRecommendationRequest = async () => {
    setIsRecommending(true)
    setIsStoppingRecommendation(false)
    setRecommendationError('')
    setConfiguratorNotice('')
    setRecommendationLogs([])
    try {
      const answers = configuratorCards.map((card, index) => {
        const values = getConfiguratorValues(index)
        return {
          cardId: card.id,
          title: card.title,
          values,
          skipped: values.length === 0,
        }
      })
      const references = referenceSelections.flatMap((selection) => {
        const movie = knownMovies.find((item) => String(item.id) === selection.id)
        return movie?.tmdbId ? [{ tmdbId: movie.tmdbId, relation: selection.relation }] : []
      })
      const job = await startRecommendationJob(answers, recommendationCount, references)
      setRecommendationJobId(job.jobId)
      setRecommendationLogs(job.logs)
    } catch (requestError) {
      setRecommendationError(
        requestError instanceof Error
          ? requestError.message
          : 'Не удалось подобрать фильмы',
      )
      setIsRecommending(false)
    }
  }

  const submitLibraryImport = async () => {
    if (!libraryImportText.trim() || isLibraryImportRunning) return
    setLibraryImportError('')
    setLibraryImportItems([])
    setSelectedImportCandidateIds(new Set())
    setLibraryImportLogs([])
    setIsLibraryImportRunning(true)
    setIsStoppingLibraryImport(false)
    try {
      const job = await startLibraryImport(libraryImportText.trim())
      setLibraryImportJobId(job.jobId)
      setLibraryImportLogs(job.logs)
    } catch (requestError) {
      setLibraryImportError(
        requestError instanceof Error ? requestError.message : 'Не удалось запустить добавление фильмов',
      )
      setIsLibraryImportRunning(false)
    }
  }

  const submitSelectedImportCandidates = async () => {
    if (selectedImportCandidateIds.size === 0 || isLibraryImportRunning) return
    setLibraryImportError('')
    setIsLibraryImportRunning(true)
    setIsStoppingLibraryImport(false)
    try {
      const job = await startCandidateLibraryImport(Array.from(selectedImportCandidateIds))
      setActiveCandidateImportIds(new Set(selectedImportCandidateIds))
      setLibraryImportJobId(job.jobId)
      setLibraryImportLogs(job.logs)
      setSelectedImportCandidateIds(new Set())
    } catch (requestError) {
      setLibraryImportError(
        requestError instanceof Error ? requestError.message : 'Не удалось добавить выбранные фильмы',
      )
      setIsLibraryImportRunning(false)
    }
  }

  const stopLibraryImport = async () => {
    if (!libraryImportJobId || isStoppingLibraryImport) return
    setIsStoppingLibraryImport(true)
    try {
      const job = await cancelLibraryImport(libraryImportJobId)
      setLibraryImportLogs(job.logs)
    } catch (requestError) {
      setLibraryImportError(
        requestError instanceof Error ? requestError.message : 'Не удалось остановить добавление',
      )
      setIsStoppingLibraryImport(false)
    }
  }

  const stopRecommendationRequest = async () => {
    if (!recommendationJobId || isStoppingRecommendation) return
    setIsStoppingRecommendation(true)
    try {
      const job = await cancelRecommendationJob(recommendationJobId)
      setRecommendationLogs(job.logs)
    } catch (requestError) {
      setRecommendationError(
        requestError instanceof Error
          ? requestError.message
          : 'Не удалось остановить подбор',
      )
      setIsStoppingRecommendation(false)
    }
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

  const submitDownloadRequest = async (tmdbMovieId: number) => {
    if (requestingMovieId !== null) {
      return
    }
    setRequestingMovieId(tmdbMovieId)
    setFailedDownloadMovieId(null)
    try {
      const [result] = await requestMoviesByTmdb([tmdbMovieId])
      setRequestedMovieIds((currentIds) => {
        const nextIds = new Set(currentIds)
        nextIds.add(result.downloadRequest.tmdbMovieId)
        return nextIds
      })
    } catch {
      setFailedDownloadMovieId(tmdbMovieId)
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

  const openTelegramSettings = async () => {
    setIsTelegramSettingsOpen(true)
    setIsMenuOpen(false)
    setTelegramSettingsStatus('')
    setTelegramChats([])
    try {
      const settings = await loadTelegramSettings()
      setTelegramConfigured(settings.configured)
      setTelegramChatId(settings.chatId ?? '')
    } catch (settingsError) {
      setTelegramSettingsStatus(
        settingsError instanceof Error ? settingsError.message : 'Не удалось загрузить настройки',
      )
    }
  }

  const submitTelegramSettings = async () => {
    setIsSavingTelegramSettings(true)
    setTelegramSettingsStatus('')
    try {
      const settings = await saveTelegramSettings({
        ...(telegramBotToken.trim() ? { botToken: telegramBotToken.trim() } : {}),
        chatId: telegramChatId.trim(),
      })
      setTelegramConfigured(settings.configured)
      setTelegramBotToken('')
      setTelegramSettingsStatus('Настройки сохранены.')
    } catch (settingsError) {
      setTelegramSettingsStatus(
        settingsError instanceof Error ? settingsError.message : 'Не удалось сохранить настройки',
      )
    } finally {
      setIsSavingTelegramSettings(false)
    }
  }

  const sendTelegramTest = async () => {
    setIsSavingTelegramSettings(true)
    setTelegramSettingsStatus('')
    try {
      await testTelegramSettings()
      setTelegramSettingsStatus('Тестовое сообщение отправлено.')
    } catch (settingsError) {
      setTelegramSettingsStatus(
        settingsError instanceof Error ? settingsError.message : 'Тест не выполнен',
      )
    } finally {
      setIsSavingTelegramSettings(false)
    }
  }

  const findPersonalTelegramChats = async () => {
    setIsFindingTelegramChats(true)
    setTelegramSettingsStatus('')
    try {
      const chats = await findTelegramChats(telegramBotToken.trim() || undefined)
      setTelegramChats(chats)
      setTelegramSettingsStatus(
        chats.length > 0
          ? 'Выберите чат, куда CineLibrary будет отправлять запросы.'
          : 'Личные чаты не найдены. Откройте своего бота в Telegram и отправьте ему /start.',
      )
    } catch (settingsError) {
      setTelegramSettingsStatus(
        settingsError instanceof Error ? settingsError.message : 'Не удалось найти чат',
      )
    } finally {
      setIsFindingTelegramChats(false)
    }
  }

  const openAPICredentials = async () => {
    setIsAPICredentialsOpen(true)
    setIsMenuOpen(false)
    setApiCredentialsStatus('')
    try {
      const settings = await loadAPICredentials()
      setReplicateConfigured(settings.replicateConfigured)
      setTmdbConfigured(settings.tmdbConfigured)
    } catch (settingsError) {
      setApiCredentialsStatus(
        settingsError instanceof Error ? settingsError.message : 'Не удалось загрузить API-ключи',
      )
    }
  }

  const submitAPICredentials = async () => {
    setIsSavingAPICredentials(true)
    setApiCredentialsStatus('')
    try {
      const settings = await saveAPICredentials({
        ...(replicateApiToken.trim() ? { replicateApiToken: replicateApiToken.trim() } : {}),
        ...(tmdbReadAccessToken.trim() ? { tmdbReadAccessToken: tmdbReadAccessToken.trim() } : {}),
      })
      setReplicateConfigured(settings.replicateConfigured)
      setTmdbConfigured(settings.tmdbConfigured)
      setReplicateApiToken('')
      setTmdbReadAccessToken('')
      setApiCredentialsStatus('API-ключи сохранены и уже используются backend.')
    } catch (settingsError) {
      setApiCredentialsStatus(
        settingsError instanceof Error ? settingsError.message : 'Не удалось сохранить API-ключи',
      )
    } finally {
      setIsSavingAPICredentials(false)
    }
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

        <div className="sidebar-label">НАСТРОЙКИ</div>
        <button className="nav-item chatbot-settings-link" onClick={openTelegramSettings}>
          <span className="nav-icon">↗</span>
          <span>
            <strong>Telegram-бот</strong>
            <small>Открыть настройки</small>
          </span>
        </button>
        <button className="nav-item chatbot-settings-link" onClick={openAPICredentials}>
          <span className="nav-icon">⌁</span>
          <span>
            <strong>API-ключи</strong>
            <small>Replicate и TMDB</small>
          </span>
        </button>
        <button type="button" className="nav-item chatbot-settings-link" aria-haspopup="dialog"
          onClick={() => { setIsMenuOpen(false); void openMediaSettings() }}>
          <span><strong>Медиатека</strong><small>Папка и исключения</small></span>
        </button>
      </aside>

      {isMediaSettingsOpen && (
        <div className="settings-overlay" role="dialog" aria-modal="true" aria-labelledby="media-settings-title"
          onClick={() => setIsMediaSettingsOpen(false)}>
          <section className="settings-modal" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="movie-modal-close" aria-label="Закрыть настройки медиатеки"
              onClick={() => setIsMediaSettingsOpen(false)}>×</button>
            <h2 id="media-settings-title">Настройки медиатеки</h2>
            <div className="media-sync-settings">
              <p>{mediaRoot || 'Папка медиатеки не подключена'}</p>
              <button type="button" className="library-import-button" disabled={isMediaSettingsBusy} onClick={() => openMediaPicker('root')}>
                {mediaRoot ? 'Сменить папку' : 'Подключить папку'}
              </button>
              {mediaRoot && (
                <>
                  <button type="button" disabled={isMediaSettingsBusy} onClick={() => void saveMediaSettings('', [])}>Отключить папку</button>
                  <button type="button" disabled={isMediaSettingsBusy} onClick={() => openMediaPicker('exclude')}>Добавить исключение</button>
                  {mediaExclusions.map((path) => (
                    <div className="media-folder-exclusion" key={path}>
                      <span>{path}</span>
                      <button type="button" disabled={isMediaSettingsBusy} aria-label={`Вернуть папку в обход: ${path}`}
                        onClick={() => void saveMediaSettings(mediaRoot, mediaExclusions.filter((item) => item !== path))}>Убрать исключение</button>
                    </div>
                  ))}
                </>
              )}
              <span role="status">{mediaSettingsMessage}</span>
            </div>
          </section>
        </div>
      )}

      {mediaPicker && (
        <dialog className="media-folder-picker" aria-labelledby="media-picker-title"
          ref={(element) => { if (element && !element.open) element.showModal() }}
          onCancel={(event) => { event.preventDefault(); if (!isMediaSettingsBusy) setMediaPicker(null) }}>
          <h2 id="media-picker-title">{mediaPicker === 'exclude' ? 'Выберите папку для исключения' : 'Выберите папку медиатеки'}</h2>
          <div className="media-folder-address">
            <button type="button" aria-label="На уровень выше" title="На уровень выше"
              disabled={isMediaSettingsBusy || !mediaFolders?.path || (mediaPicker === 'exclude' && mediaFolders.path === mediaRoot)}
              onClick={() => void loadMediaFolders(mediaFolders?.parent ?? null)}>↑</button>
            <p title={mediaFolders?.path ?? undefined}>{mediaFolders?.path ?? 'Этот компьютер'}</p>
          </div>
          <div className="media-folder-list" aria-label="Доступные папки" aria-busy={isMediaSettingsBusy}>
            {mediaFolders?.folders.map((folder) => (
              <button type="button" className="media-folder-row" key={folder.path} disabled={isMediaSettingsBusy}
                onClick={() => void loadMediaFolders(folder.path)}>
                <span className={mediaFolders.path ? 'media-folder-icon' : 'media-drive-icon'} aria-hidden="true" />
                <span>{folder.name}</span>
                <span className="media-folder-arrow" aria-hidden="true">›</span>
              </button>
            ))}
            {mediaFolders?.folders.length === 0 && !isMediaSettingsBusy && <p>В этой папке нет подпапок.</p>}
            {isMediaSettingsBusy && <p role="status">Открываем папку…</p>}
            {mediaSettingsMessage && <p role="status">{mediaSettingsMessage}</p>}
          </div>
          <div className="configurator-actions">
            <button type="button" className="configurator-secondary" disabled={isMediaSettingsBusy}
              onClick={() => setMediaPicker(null)}>Отмена</button>
            <button type="button" className="configurator-primary"
              disabled={isMediaSettingsBusy || !mediaFolders?.path || (mediaPicker === 'exclude' && mediaFolders.path === mediaRoot)}
              onClick={() => {
                const path = mediaFolders?.path
                if (!path) return
                if (mediaPicker === 'root') void saveMediaSettings(path, path === mediaRoot ? mediaExclusions : [])
                else void saveMediaSettings(mediaRoot, [...new Set([...mediaExclusions, path])])
              }}>{mediaPicker === 'root' ? 'Выбрать папку' : 'Исключить папку'}</button>
          </div>
        </dialog>
      )}

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

          <div className="welcome-actions">
            <button
              className="library-import-button"
              onClick={() => setIsLibraryImportOpen(true)}
            >
              Добавить просмотренные фильмы
            </button>
            <button type="button" className="library-import-button" disabled={isMediaSyncing} onClick={() => void syncMedia()}>
              {isMediaSyncing ? 'Синхронизация…' : 'Синхронизация медиатеки'}
            </button>
            <button
              className="add-button"
              onClick={() => {
                if (isRecommending) {
                  setIsConfiguratorSummary(true)
                } else if (!recommendationResult) {
                  setRecommendationError('')
                  setRecommendationLogs([])
                  setConfiguratorStep(0)
                  setIsConfiguratorSummary(false)
                }
                setIsRecommendationOpen(true)
              }}
            >
              Подобрать фильмы
            </button>
          </div>
          {mediaSyncMessage && <p className="media-sync-message" role="status">{mediaSyncMessage}</p>}
          {mediaPending.length > 0 && (
            <details className="media-sync-message">
              <summary>Требуют проверки: {mediaPending.length}</summary>
              <ul>{mediaPending.map((name, index) => <li key={`${name}-${index}`}>{name}</li>)}</ul>
            </details>
          )}
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
              value={availability}
              onChange={(event) => setAvailability(event.target.value as AvailabilityStatus | '')}
              aria-label="Наличие на диске"
            >
              <option value="">Наличие на диске: все</option>
              {Object.entries(availabilityLabels).map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
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
                className={`movie-card status-${movie.availability}`}
                key={movie.id}
              >
                <button
                  className="movie-poster-button"
                  onClick={() => openMovie(movie)}
                  aria-label={`Подробнее о фильме ${movie.title}`}
                >
                  <div
                    className="movie-poster"
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

      {isLibraryImportOpen && (
        <div
          className="movie-modal-overlay"
          onClick={() => setIsLibraryImportOpen(false)}
        >
          <section
            className="movie-modal library-import-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="library-import-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="movie-modal-close"
              onClick={() => setIsLibraryImportOpen(false)}
              aria-label="Закрыть добавление фильмов"
            >
              ×
            </button>
            <div className="eyebrow">MOVIE LIBRARIAN 1</div>
            <h2 id="library-import-title">Добавить просмотренные фильмы</h2>
            <label className="library-import-field">
              <span>Список фильмов</span>
              <textarea
                rows={10}
                value={libraryImportText}
                disabled={isLibraryImportRunning}
                onChange={(event) => setLibraryImportText(event.target.value)}
                placeholder="Вставьте список фильмов"
              />
            </label>

            {libraryImportLogs.length > 0 && (
              <div className="recommendation-log" aria-live="polite">
                <strong>Ход добавления</strong>
                <ol>
                  {libraryImportLogs.map((entry) => (
                    <li key={entry.sequence}>
                      <time>{new Date(entry.createdAt).toLocaleTimeString('ru-RU')}</time>
                      <span>{entry.message}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {libraryImportItems.length > 0 && (
              <div className="library-import-results">
                {libraryImportItems.map((item, index) => (
                  <article key={`${item.inputText}-${index}`}>
                    <strong>{item.title || item.inputText}</strong>
                    <span>
                      {item.status === 'imported' && 'Добавлен в дневник'}
                      {item.status === 'updated' && 'Уже был в базе — отмечен просмотренным'}
                      {item.status === 'ambiguous' && 'Не удалось однозначно определить'}
                      {item.status === 'not_found' && 'Не найден'}
                      {item.status === 'failed' && 'Ошибка обработки'}
                    </span>
                    {item.issues.length > 0 && <small>{item.issues.join(' ')}</small>}
                    {item.status === 'ambiguous' && item.candidates.length > 0 && (
                      <div className="library-import-candidates">
                        <strong>Выберите подходящий вариант</strong>
                        <div>
                          {item.candidates.map((candidate) => {
                            const selected = selectedImportCandidateIds.has(candidate.tmdbId)
                            return (
                              <label
                                className={selected ? 'is-selected' : ''}
                                key={candidate.tmdbId}
                              >
                                <input
                                  type="checkbox"
                                  checked={selected}
                                  disabled={isLibraryImportRunning}
                                  onChange={() => setSelectedImportCandidateIds((currentIds) => {
                                    const nextIds = new Set(currentIds)
                                    if (nextIds.has(candidate.tmdbId)) {
                                      nextIds.delete(candidate.tmdbId)
                                    } else {
                                      nextIds.add(candidate.tmdbId)
                                    }
                                    return nextIds
                                  })}
                                />
                                <span>
                                  <b>{candidate.originalTitle}</b>
                                  <small>{candidate.releaseYear || 'Год неизвестен'}</small>
                                </span>
                              </label>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}

            {libraryImportError && (
              <p className="configurator-error">{libraryImportError}</p>
            )}

            <div className="configurator-actions">
              {isLibraryImportRunning ? (
                <button
                  type="button"
                  className="configurator-stop"
                  disabled={isStoppingLibraryImport}
                  onClick={stopLibraryImport}
                >
                  {isStoppingLibraryImport ? 'Останавливаем…' : 'Прервать'}
                </button>
              ) : (
                <button
                  type="button"
                  className="configurator-primary"
                  disabled={!libraryImportText.trim()}
                  onClick={submitLibraryImport}
                >
                  Добавить фильмы
                </button>
              )}
            </div>
            {!isLibraryImportRunning && selectedImportCandidateIds.size > 0 && (
              <div className="library-import-batch-action">
                <span>Выбрано вариантов: {selectedImportCandidateIds.size}</span>
                <button type="button" onClick={submitSelectedImportCandidates}>
                  Добавить выбранные в каталог
                </button>
              </div>
            )}
          </section>
        </div>
      )}

      {isRecommendationOpen && (
        <div
          className="recommendation-overlay"
          onClick={() => setIsRecommendationOpen(false)}
        >
          <section
            className={`recommendation-modal ${
              recommendationResult ? 'has-results' : ''
            }`}
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
                {recommendationResult
                  ? 'Рекомендации'
                  : isConfiguratorSummary
                    ? 'Сводка запроса'
                    : 'Подбор фильмов'}
              </h2>
              {!recommendationResult && (
                <p>
                  {isConfiguratorSummary
                    ? 'Проверьте ответы и при необходимости вернитесь к нужной карточке.'
                    : `Карточка ${configuratorStep + 1} из ${configuratorCards.length}`}
                </p>
              )}
            </header>

            {recommendationResult ? (
              <RecommendationResults
                key={recommendationResult.sessionId}
                result={recommendationResult}
                requestedCount={recommendationCount}
                knownMovies={knownMovies}
                onBack={() => setRecommendationResult(null)}
                onDelivered={(ids) => setRequestedMovieIds((current) => new Set([...current, ...ids]))}
              />
            ) : isConfiguratorSummary ? (
              <section className="configurator-summary">
                {configuratorCards.map((card, index) => {
                  const values = getConfiguratorValues(index)
                  return (
                  <article key={card.id}>
                    <div>
                      <span>{index + 1}. {card.title}</span>
                      <strong>{card.question}</strong>
                      <small>
                        {values.length > 0 ? values.join(' · ') : 'Пропущено'}
                      </small>
                    </div>
                    <button
                      type="button"
                      disabled={isRecommending}
                      onClick={() => editConfiguratorCard(index)}
                    >
                      Изменить
                    </button>
                  </article>
                  )
                })}

                {configuratorNotice && (
                  <p className="configurator-notice">{configuratorNotice}</p>
                )}
                {recommendationLogs.length > 0 && (
                  <div className="recommendation-log" aria-live="polite">
                    <strong>Ход подбора</strong>
                    <ol>
                      {recommendationLogs.map((entry) => (
                        <li key={entry.sequence}>
                          <time>
                            {new Date(entry.createdAt).toLocaleTimeString('ru-RU')}
                          </time>
                          <span>{entry.message}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
                {recommendationError && (
                  <p className="configurator-error">{recommendationError}</p>
                )}

                <label className="recommendation-count">
                  <span>Количество фильмов</span>
                  <select
                    value={recommendationCount}
                    disabled={isRecommending}
                    onChange={(event) =>
                      setRecommendationCount(Number(event.target.value))
                    }
                  >
                    {[3, 5, 7, 10].map((count) => (
                      <option value={count} key={count}>{count}</option>
                    ))}
                  </select>
                </label>

                <div className="configurator-actions">
                  <button
                    type="button"
                    className="configurator-secondary"
                    disabled={isRecommending}
                    onClick={() => {
                      configuratorCards.forEach((_card, index) =>
                        clearConfiguratorCard(index),
                      )
                      setConfiguratorStep(0)
                      setIsConfiguratorSummary(false)
                      setConfiguratorNotice('')
                      setRecommendationError('')
                      setRecommendationLogs([])
                    }}
                  >
                    Пройти заново
                  </button>
                  {isRecommending ? (
                    <button
                      type="button"
                      className="configurator-stop"
                      disabled={isStoppingRecommendation}
                      onClick={stopRecommendationRequest}
                    >
                      {isStoppingRecommendation ? 'Останавливаем…' : 'Прервать'}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="configurator-primary"
                      onClick={submitRecommendationRequest}
                    >
                      Подобрать
                    </button>
                  )}
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

                <div className="configurator-card-heading">
                  <span>{configuratorCards[configuratorStep].title}</span>
                  <h3>{configuratorCards[configuratorStep].question}</h3>
                </div>

                {configuratorStep === 0 && (
                  <label className="configurator-wish">
                    <span>Опишите пожелание своими словами</span>
                    <textarea
                      rows={7}
                      maxLength={4000}
                      value={configuratorWish}
                      onChange={(event) => setConfiguratorWish(event.target.value)}
                      placeholder="Например: хочу напряжённый фильм на вечер, но без тяжёлого финала. Смотреть будем вдвоём, времени около двух часов."
                    />
                  </label>
                )}

                {configuratorStep === 1 && (
                  <div className="configurator-selector">
                    <div className="configurator-library-controls">
                      <input
                        type="search"
                        value={configuratorSearch}
                        onChange={(event) => setConfiguratorSearch(event.target.value)}
                        placeholder="Название фильма"
                        aria-label="Поиск фильма-ориентира"
                      />
                      <select
                        value={referenceGenre}
                        onChange={(event) => setReferenceGenre(event.target.value)}
                        aria-label="Фильтр фильмов-ориентиров по жанру"
                      >
                        <option value="">Все жанры</option>
                        {knownGenres.map((item) => (
                          <option value={item} key={item}>{item}</option>
                        ))}
                      </select>
                      <select
                        value={referenceSort}
                        onChange={(event) => setReferenceSort(event.target.value as LibrarySort)}
                        aria-label="Сортировка фильмов-ориентиров"
                      >
                        <option value="release_desc">Сначала новые</option>
                        <option value="release_asc">Сначала старые</option>
                        <option value="title_asc">По названию</option>
                        <option value="rating_desc">По моей оценке</option>
                      </select>
                    </div>
                    {!normalizedReferenceSearch && !referenceGenre && (
                      <p className="configurator-search-hint">
                        Начните вводить название — результаты появятся здесь.
                      </p>
                    )}
                    {(normalizedReferenceSearch || referenceGenre) && referenceResults.length === 0 && (
                      <p className="configurator-search-hint">Фильмы не найдены.</p>
                    )}
                    <div className="configurator-choice-list configurator-movie-results">
                      {referenceResults.map((movie) => {
                          const selected = referenceSelections.find(
                            (item) => item.id === String(movie.id),
                          )
                          return (
                            <label key={movie.id}>
                              {movie.poster ? (
                                <img src={movie.poster} alt="" />
                              ) : (
                                <span className="configurator-poster-fallback">Нет постера</span>
                              )}
                              <span>
                                <strong>{movie.title}</strong>
                                {movie.originalTitle !== movie.title && (
                                  <small>{movie.originalTitle}</small>
                                )}
                                <small>{movie.year} · {movie.genre}</small>
                              </span>
                              <select
                                value={selected?.relation ?? ''}
                                onChange={(event) =>
                                  setReferenceSelections((current) =>
                                    updateSelection(
                                      current,
                                      String(movie.id),
                                      `${movie.title} (${movie.year})`,
                                      event.target.value as ReferenceRelation | '',
                                    ),
                                  )
                                }
                              >
                                <option value="">Не учитывать</option>
                                <option value="similar">Похожее</option>
                                <option value="avoid">Не похожее</option>
                              </select>
                            </label>
                          )
                        })}
                    </div>
                    {referenceSelections.length > 0 && (
                      <div className="configurator-selected-items">
                        <strong>Выбрано</strong>
                        {referenceSelections.map((item) => (
                          <button
                            type="button"
                            key={item.id}
                            onClick={() => setReferenceSelections((current) =>
                              current.filter((selection) => selection.id !== item.id))}
                          >
                            {item.label} ×
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {configuratorStep === 2 && (
                  <div className="configurator-selector">
                    <div className="configurator-genre-filter">
                      <select
                        value={genreCandidate}
                        onChange={(event) => setGenreCandidate(event.target.value)}
                        aria-label="Выберите жанр"
                      >
                        <option value="">Выберите жанр</option>
                        {knownGenres.map((item) => (
                          <option value={item} key={item}>{item}</option>
                        ))}
                      </select>
                      <select
                        value={genreCandidateRelation}
                        onChange={(event) => setGenreCandidateRelation(
                          event.target.value as PreferenceRelation,
                        )}
                        aria-label="Значение жанра для подбора"
                      >
                        <option value="prefer">Желательно</option>
                        <option value="require">Обязательно</option>
                        <option value="exclude">Исключить</option>
                      </select>
                      <button
                        type="button"
                        disabled={!genreCandidate}
                        onClick={() => {
                          setGenreSelections((current) => updateSelection(
                            current,
                            genreCandidate,
                            genreCandidate,
                            genreCandidateRelation,
                          ))
                          setGenreCandidate('')
                        }}
                      >
                        Добавить
                      </button>
                    </div>
                    <div className="configurator-choice-list">
                      {genreSelections.map((item) => (
                        <label key={item.id}>
                          <strong>{item.label}</strong>
                          <select
                            value={item.relation}
                            onChange={(event) => setGenreSelections((current) =>
                              updateSelection(
                                current,
                                item.id,
                                item.label,
                                event.target.value as PreferenceRelation | '',
                              ))}
                          >
                            <option value="prefer">Желательно</option>
                            <option value="require">Обязательно</option>
                            <option value="exclude">Исключить</option>
                            <option value="">Удалить</option>
                          </select>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {configuratorStep === 3 && (
                  <div className="configurator-constraints">
                    <label>
                      <span>Год выпуска от</span>
                      <input
                        type="number"
                        min="1888"
                        max="2200"
                        value={configuratorConstraints.yearFrom}
                        onChange={(event) => setConfiguratorConstraints(
                          (current) => ({ ...current, yearFrom: event.target.value }),
                        )}
                      />
                    </label>
                    <label>
                      <span>Год выпуска до</span>
                      <input
                        type="number"
                        min="1888"
                        max="2200"
                        value={configuratorConstraints.yearTo}
                        onChange={(event) => setConfiguratorConstraints(
                          (current) => ({ ...current, yearTo: event.target.value }),
                        )}
                      />
                    </label>
                    <label>
                      <span>Не дольше, минут</span>
                      <input
                        type="number"
                        min="1"
                        max="1000"
                        value={configuratorConstraints.maxRuntimeMinutes}
                        onChange={(event) => setConfiguratorConstraints(
                          (current) => ({
                            ...current,
                            maxRuntimeMinutes: event.target.value,
                          }),
                        )}
                      />
                    </label>
                    {[
                      ['country', 'Страна'],
                      ['certification', 'Возрастной рейтинг'],
                      ['language', 'Язык'],
                    ].map(([field, label]) => (
                      <label key={field}>
                        <span>{label}</span>
                        <input
                          type="text"
                          value={configuratorConstraints[
                            field as 'country' | 'certification' | 'language'
                          ]}
                          onChange={(event) => setConfiguratorConstraints(
                            (current) => ({
                              ...current,
                              [field]: event.target.value,
                            }),
                          )}
                        />
                      </label>
                    ))}
                  </div>
                )}

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
                {selectedMovie.availability !== 'available' && selectedMovieTmdbId !== null && (
                  <div className="movie-modal-download">
                    <button
                      type="button"
                      className="movie-download-button"
                      disabled={requestingMovieId !== null}
                      onClick={() => submitDownloadRequest(selectedMovieTmdbId)}
                    >
                      {requestingMovieId === selectedMovieTmdbId
                        ? 'Отправляем…'
                        : 'Запросить загрузку'}
                    </button>
                    {failedDownloadMovieId === selectedMovieTmdbId && (
                      <span className="movie-download-error" role="alert">
                        Не удалось отправить запрос на загрузку. Попробуйте ещё раз.
                      </span>
                    )}
                  </div>
                )}
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
                            hoverFilmographyItem(
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
                          onBlur={scheduleFilmographyPreviewClose}
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
                            hoverFilmographyItem(event.currentTarget, credit, null)
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
            bottom: filmographyPreview.bottom,
            maxHeight: filmographyPreview.maxHeight,
            left: filmographyPreview.left,
            width: filmographyPreview.width,
          }}
          onMouseEnter={keepFilmographyPreviewOpen}
          onMouseLeave={scheduleFilmographyPreviewClose}
          onFocus={keepFilmographyPreviewOpen}
          onBlur={scheduleFilmographyPreviewClose}
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
                  className="movie-download-button"
                  disabled={requestingMovieId !== null}
                  onClick={() => submitDownloadRequest(filmographyPreview.tmdbMovieId)}
                >
                  {requestingMovieId === filmographyPreview.tmdbMovieId
                    ? 'Отправляем…'
                    : 'Запросить загрузку'}
                </button>
              )}
              {requestedMovieIds.has(filmographyPreview.tmdbMovieId) && (
                <span className="movie-download-requested">
                  Запрос отправлен
                </span>
              )}
              {filmographyPreview.availability === 'downloading' && (
                <span className="filmography-preview-downloading">
                  Скачивается
                </span>
              )}
            </span>
            {failedDownloadMovieId === filmographyPreview.tmdbMovieId && (
              <span className="movie-download-error" role="alert">
                Не удалось отправить запрос на загрузку. Попробуйте ещё раз.
              </span>
            )}
          </span>
        </div>
      )}

      {isTelegramSettingsOpen && (
        <div
          className="settings-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="telegram-settings-title"
          onClick={() => setIsTelegramSettingsOpen(false)}
        >
          <section className="settings-modal" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="movie-modal-close"
              onClick={() => setIsTelegramSettingsOpen(false)}
              aria-label="Закрыть настройки"
            >
              ×
            </button>
            <span className="eyebrow">ЛИЧНЫЙ TELEGRAM-БОТ</span>
            <h2 id="telegram-settings-title">Настройка Telegram-бота</h2>
            <p>
              Запросы на загрузку будут приходить в ваш личный чат с вашим ботом.
            </p>
            <ol className="telegram-setup-help">
              <li>Создайте собственного бота через BotFather и скопируйте Bot Token.</li>
              <li>Откройте этого бота в Telegram и отправьте ему команду <code>/start</code>.</li>
              <li>Нажмите «Найти личный чат», выберите найденный чат и сохраните настройки.</li>
            </ol>
            <label>
              <span>Bot Token — токен, полученный от BotFather</span>
              <input
                type="password"
                value={telegramBotToken}
                placeholder={telegramConfigured ? 'Оставьте пустым, чтобы не менять' : 'Токен от BotFather'}
                onChange={(event) => setTelegramBotToken(event.target.value)}
                autoComplete="off"
              />
            </label>
            <button
              type="button"
              className="telegram-find-chat"
              disabled={isFindingTelegramChats || (!telegramBotToken.trim() && !telegramConfigured)}
              onClick={findPersonalTelegramChats}
            >
              {isFindingTelegramChats ? 'Ищем чат…' : 'Найти личный чат'}
            </button>
            {telegramChats.length > 0 && (
              <div className="telegram-chat-options">
                {telegramChats.map((chat) => (
                  <button
                    type="button"
                    className={telegramChatId === chat.chatId ? 'is-selected' : ''}
                    key={chat.chatId}
                    onClick={() => setTelegramChatId(chat.chatId)}
                  >
                    <strong>{chat.label}</strong>
                    <small>Chat ID: {chat.chatId}</small>
                  </button>
                ))}
              </div>
            )}
            <label>
              <span>Chat ID — числовой идентификатор вашего личного чата</span>
              <input
                type="text"
                value={telegramChatId}
                onChange={(event) => setTelegramChatId(event.target.value)}
              />
            </label>
            {telegramSettingsStatus && <p className="settings-status">{telegramSettingsStatus}</p>}
            <div className="settings-actions">
              <button
                type="button"
                onClick={sendTelegramTest}
                disabled={!telegramConfigured || isSavingTelegramSettings}
              >
                Проверить
              </button>
              <button
                type="button"
                className="settings-save"
                onClick={submitTelegramSettings}
                disabled={!telegramChatId.trim() || isSavingTelegramSettings}
              >
                {isSavingTelegramSettings ? 'Сохраняем…' : 'Сохранить'}
              </button>
            </div>
          </section>
        </div>
      )}

      {isAPICredentialsOpen && (
        <div
          className="settings-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="api-credentials-title"
          onClick={() => setIsAPICredentialsOpen(false)}
        >
          <section className="settings-modal" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="movie-modal-close"
              onClick={() => setIsAPICredentialsOpen(false)}
              aria-label="Закрыть настройки API"
            >
              ×
            </button>
            <span className="eyebrow">ИНТЕГРАЦИИ</span>
            <h2 id="api-credentials-title">API-ключи</h2>
            <p>
              Ключи сохраняются локально и автоматически подключаются при каждом запуске backend.
            </p>
            <label>
              <span>Replicate API Token — доступ к Google Gemini 3 Flash</span>
              <input
                type="password"
                value={replicateApiToken}
                placeholder={replicateConfigured ? 'Настроен — оставьте пустым, чтобы не менять' : 'r8_…'}
                onChange={(event) => setReplicateApiToken(event.target.value)}
                autoComplete="off"
              />
            </label>
            <label>
              <span>TMDB Read Access Token — данные о фильмах и людях</span>
              <input
                type="password"
                value={tmdbReadAccessToken}
                placeholder={tmdbConfigured ? 'Настроен — оставьте пустым, чтобы не менять' : 'Токен TMDB API Read Access'}
                onChange={(event) => setTmdbReadAccessToken(event.target.value)}
                autoComplete="off"
              />
            </label>
            {apiCredentialsStatus && <p className="settings-status">{apiCredentialsStatus}</p>}
            <div className="settings-actions">
              <button
                type="button"
                className="settings-save"
                onClick={submitAPICredentials}
                disabled={
                  isSavingAPICredentials
                  || (!replicateApiToken.trim() && !replicateConfigured)
                  || (!tmdbReadAccessToken.trim() && !tmdbConfigured)
                }
              >
                {isSavingAPICredentials ? 'Сохраняем…' : 'Сохранить ключи'}
              </button>
            </div>
          </section>
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
