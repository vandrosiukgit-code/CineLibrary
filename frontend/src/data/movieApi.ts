import type {
  AvailabilityStatus,
  MovieCredit,
  MovieRecord,
  MovieUserDataUpdate,
} from './movieCatalog'

const API_URL = 'http://127.0.0.1:8000/api/movies'

export type LibraryFilter =
  | 'all'
  | 'watched'
  | 'wishlist'
  | AvailabilityStatus

export interface MovieView {
  id: number
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
  availability: AvailabilityStatus
  watched: boolean
  personalRating: number | null
  feedbackTags: string[]
  comment: string
  isNew: boolean
  inWishlist: boolean
}

function toMovieView(movie: MovieRecord): MovieView {
  return {
    id: movie.id,
    title: movie.title,
    originalTitle: movie.originalTitle,
    year: movie.releaseYear,
    genre: movie.genres[0]?.displayName ?? 'Без жанра',
    genres: movie.genres.map((genre) => genre.displayName),
    rating: movie.imdbRating,
    poster: movie.posterUrl,
    overview: movie.overview,
    director:
      movie.credits.find((credit) => credit.creditType === 'director') ?? null,
    actors: movie.credits.filter((credit) => credit.creditType === 'actor'),
    availability: movie.availability,
    watched: movie.userData.watched,
    personalRating: movie.userData.personalRating,
    feedbackTags: movie.userData.tags,
    comment: movie.userData.comment,
    isNew: movie.isNew,
    inWishlist: movie.userData.inWishlist,
  }
}

export async function loadMovies(
  search: string,
  filter: LibraryFilter,
  signal?: AbortSignal,
): Promise<MovieView[]> {
  const parameters = new URLSearchParams()
  if (search.trim()) parameters.set('search', search.trim())
  if (filter === 'watched') parameters.set('watched', 'true')
  if (filter === 'wishlist') parameters.set('inWishlist', 'true')
  if (['available', 'downloading', 'missing'].includes(filter)) {
    parameters.set('availability', filter)
  }

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
