import type {
  AvailabilityStatus,
  MovieCredit,
  MovieRecord,
  MovieUserDataUpdate,
} from './movieCatalog'

const API_URL = '/api/movies'

export type LibraryFilter =
  | 'all'
  | 'high-rated'
  | 'rewatch'
  | 'disliked'
  | 'unrated'
  | 'untagged'

export type LibrarySort =
  | 'release_desc'
  | 'release_asc'
  | 'title_asc'
  | 'rating_desc'

export interface LibraryOptions {
  genre: string
  sort: LibrarySort
  availability?: AvailabilityStatus | ''
}

export interface MovieView {
  id: number
  tmdbId: number | null
  title: string
  originalTitle: string
  year: number
  genre: string
  genres: string[]
  rating: number | null
  poster: string | null
  overview: string
  director: MovieCredit | null
  actors: MovieCredit[]
  people: MovieCredit[]
  availability: AvailabilityStatus
  watched: boolean
  personalRating: number | null
  feedbackTags: string[]
  feedbackTagCodes: string[]
  comment: string
  isNew: boolean
  inWishlist: boolean
}

function toMovieView(movie: MovieRecord): MovieView {
  return {
    id: movie.id,
    tmdbId: movie.tmdbId,
    title: movie.title,
    originalTitle: movie.originalTitle,
    year: movie.releaseYear,
    genre: movie.genres[0]?.displayName ?? 'Без жанра',
    genres: movie.genres.map((genre) => genre.displayName),
    rating: movie.imdbRating ?? movie.tmdbRating,
    poster: movie.posterUrl,
    overview: movie.overview,
    director:
      movie.credits.find((credit) => credit.creditType === 'director') ?? null,
    actors: movie.credits.filter((credit) => credit.creditType === 'actor'),
    people: movie.credits,
    availability: movie.availability,
    watched: movie.userData.watched,
    personalRating: movie.userData.personalRating,
    feedbackTags: movie.userData.tags,
    feedbackTagCodes: movie.userData.tagCodes,
    comment: movie.userData.comment,
    isNew: movie.isNew,
    inWishlist: movie.userData.inWishlist,
  }
}

export interface TasteTagDefinition {
  code: string
  label: string
  category: 'viewing' | 'emotion' | 'strength' | 'weakness' | 'outcome'
  sentiment: -1 | 0 | 1
  sortOrder: number
}

export interface DownloadRequest {
  id: number
  tmdbMovieId: number
  localMovieId: number | null
  title: string
  internationalTitle: string | null
  fileName: string | null
  telegramMessageId: number | null
  status: 'requested' | 'completed' | 'cancelled'
  requestedAt: string
}

export interface TelegramSettings {
  configured: boolean
  chatId: string | null
  updatedAt: string | null
}

export interface TelegramChat {
  chatId: string
  label: string
}

export interface APICredentialsSettings {
  replicateConfigured: boolean
  tmdbConfigured: boolean
  updatedAt: string | null
}

async function readApiError(response: Response, fallback: string) {
  const body = (await response.json().catch(() => null)) as
    | { detail?: string }
    | null
  return new Error(body?.detail || fallback)
}

export async function loadTelegramSettings(): Promise<TelegramSettings> {
  const response = await fetch(`${API_URL}/telegram-settings`)
  if (!response.ok) throw await readApiError(response, 'Не удалось загрузить настройки')
  return (await response.json()) as TelegramSettings
}

export async function saveTelegramSettings(input: {
  botToken?: string
  chatId: string
}): Promise<TelegramSettings> {
  const response = await fetch(`${API_URL}/telegram-settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw await readApiError(response, 'Не удалось сохранить настройки')
  return (await response.json()) as TelegramSettings
}

export async function testTelegramSettings(): Promise<void> {
  const response = await fetch(`${API_URL}/telegram-settings/test`, {
    method: 'POST',
  })
  if (!response.ok) throw await readApiError(response, 'Тестовое сообщение не отправлено')
}

export async function findTelegramChats(botToken?: string): Promise<TelegramChat[]> {
  const response = await fetch(`${API_URL}/telegram-settings/chats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(botToken ? { botToken } : {}),
  })
  if (!response.ok) throw await readApiError(response, 'Не удалось найти личный чат')
  return (await response.json()) as TelegramChat[]
}

export async function loadAPICredentials(): Promise<APICredentialsSettings> {
  const response = await fetch('/api/settings/api-credentials')
  if (!response.ok) throw await readApiError(response, 'Не удалось загрузить API-ключи')
  return (await response.json()) as APICredentialsSettings
}

export async function saveAPICredentials(input: {
  replicateApiToken?: string
  tmdbReadAccessToken?: string
}): Promise<APICredentialsSettings> {
  const response = await fetch('/api/settings/api-credentials', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw await readApiError(response, 'Не удалось сохранить API-ключи')
  return (await response.json()) as APICredentialsSettings
}

export async function loadDownloadRequests(
  signal?: AbortSignal,
): Promise<DownloadRequest[]> {
  const response = await fetch(`${API_URL}/download-requests`, { signal })
  if (!response.ok) throw new Error('Не удалось загрузить запросы на загрузку')
  return (await response.json()) as DownloadRequest[]
}

export async function requestMovieDownload(input: {
  tmdbMovieId: number
  localMovieId: number | null
  title: string
}): Promise<DownloadRequest> {
  const response = await fetch(`${API_URL}/download-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!response.ok) throw new Error('Не удалось отправить запрос на загрузку')
  return (await response.json()) as DownloadRequest
}

export class DownloadDeliveryError extends Error {
  readonly deliveredTmdbIds: number[]

  constructor(message: string, deliveredTmdbIds: number[]) {
    super(message)
    this.deliveredTmdbIds = deliveredTmdbIds
  }
}

export async function requestMoviesByTmdb(
  tmdbMovieIds: number[],
  options?: { preferPosters: boolean },
): Promise<Array<{ movie: MovieRecord; downloadRequest: DownloadRequest }>> {
  const response = await fetch(`${API_URL}/download-requests/by-tmdb`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tmdbMovieIds, ...options }),
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string | { message?: string; deliveredTmdbIds?: number[] } }
      | null
    const detail = body?.detail
    throw new DownloadDeliveryError(
      (typeof detail === 'string' ? detail : detail?.message) || 'Не удалось отправить заявку',
      typeof detail === 'object' ? detail?.deliveredTmdbIds ?? [] : [],
    )
  }
  return (await response.json()) as Array<{
    movie: MovieRecord
    downloadRequest: DownloadRequest
  }>
}

export async function loadTasteTags(
  signal?: AbortSignal,
): Promise<TasteTagDefinition[]> {
  const response = await fetch(`${API_URL}/taste-tags`, { signal })
  if (!response.ok) throw new Error('Не удалось загрузить теги впечатлений')
  return (await response.json()) as TasteTagDefinition[]
}

export async function loadGenres(signal?: AbortSignal): Promise<string[]> {
  const response = await fetch(`${API_URL}/genres?watched=true`, { signal })
  if (!response.ok) throw new Error('Не удалось загрузить жанры')
  return (await response.json()) as string[]
}

export async function loadMovies(
  search: string,
  filter: LibraryFilter,
  options: LibraryOptions,
  signal?: AbortSignal,
): Promise<MovieView[]> {
  const parameters = new URLSearchParams()
  parameters.set('watched', 'true')
  if (search.trim()) parameters.set('search', search.trim())
  if (filter === 'high-rated') parameters.set('personalRatingMin', '4')
  if (filter === 'rewatch') parameters.set('tagCode', 'outcome:rewatch')
  if (filter === 'disliked') parameters.set('personalRatingMax', '2')
  if (filter === 'unrated') parameters.set('hasPersonalRating', 'false')
  if (filter === 'untagged') parameters.set('hasTasteTags', 'false')
  if (options.genre) parameters.set('genre', options.genre)
  if (options.availability) parameters.set('availability', options.availability)
  parameters.set('sort', options.sort)

  const query = parameters.size > 0 ? `?${parameters}` : ''
  const response = await fetch(`${API_URL}${query}`, { signal })
  if (!response.ok) throw new Error('Не удалось загрузить фильмы')
  return ((await response.json()) as MovieRecord[]).map(toMovieView)
}

export async function saveUserData(
  movieId: number,
  changes: MovieUserDataUpdate,
): Promise<MovieView> {
  const response = await fetch(`${API_URL}/${movieId}/user-data`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (!response.ok) throw new Error('Не удалось сохранить личные отметки')
  return toMovieView((await response.json()) as MovieRecord)
}
