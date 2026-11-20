import type { MovieRecord } from './movieCatalog'

const API_URL = 'http://127.0.0.1:8000/api/agents/movie-recommender'

export interface ConfiguratorAnswer {
  cardId: string
  title: string
  values: string[]
  skipped: boolean
}

export interface SuggestedMovie {
  title: string
  originalTitle: string | null
  releaseYear: number | null
  relevance: number
}

export interface TemporaryPerson {
  tmdbId: number
  name: string
  displayName: string
  profileUrl: string | null
  inPeopleDatabase: boolean
}

export interface TemporaryMovieCard {
  title: string
  originalTitle: string
  releaseYear: number
  tmdbId: number
  runtimeMinutes: number | null
  overview: string | null
  posterUrl: string | null
  genres: Array<{ canonicalName: string; displayName: string }>
  tmdbRating: number | null
}

export interface TemporaryRecommendation {
  id: string
  suggestion: SuggestedMovie
  status: 'draft_ready' | 'already_exists' | 'ambiguous' | 'not_found' | 'failed'
  movie: TemporaryMovieCard | null
  existingMovieId: number | null
  people: TemporaryPerson[]
  issues: string[]
}

export interface RecommendationResponse {
  sessionId: string
  tasteProfile: Record<string, unknown>
  prompt: string
  movies: TemporaryRecommendation[]
}

export interface RecommendationJobLog {
  sequence: number
  createdAt: string
  message: string
}

export interface RecommendationJob {
  jobId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  logs: RecommendationJobLog[]
  result: RecommendationResponse | null
  error: string | null
}

async function readError(response: Response, fallback: string): Promise<Error> {
  const body = (await response.json().catch(() => null)) as
    | { detail?: string }
    | null
  return new Error(body?.detail || fallback)
}

export async function startRecommendationJob(
  answers: ConfiguratorAnswer[],
  count: number,
): Promise<RecommendationJob> {
  const response = await fetch(`${API_URL}/recommend/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, count }),
  })
  if (!response.ok) {
    throw await readError(response, 'Не удалось запустить подбор фильмов')
  }
  return (await response.json()) as RecommendationJob
}

export async function loadRecommendationJob(
  jobId: string,
): Promise<RecommendationJob> {
  const response = await fetch(`${API_URL}/recommend/jobs/${jobId}`)
  if (!response.ok) {
    throw await readError(response, 'Не удалось получить состояние подбора')
  }
  return (await response.json()) as RecommendationJob
}

export async function cancelRecommendationJob(
  jobId: string,
): Promise<RecommendationJob> {
  const response = await fetch(`${API_URL}/recommend/jobs/${jobId}/cancel`, {
    method: 'POST',
  })
  if (!response.ok) {
    throw await readError(response, 'Не удалось остановить подбор')
  }
  return (await response.json()) as RecommendationJob
}

export async function promoteRecommendation(
  sessionId: string,
  recommendationId: string,
): Promise<{ movie: MovieRecord; downloadRequestId: number }> {
  const response = await fetch(`${API_URL}/sessions/${sessionId}/promote`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recommendationId }),
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null
    throw new Error(body?.detail || 'Не удалось отправить фильм на загрузку')
  }
  return (await response.json()) as {
    movie: MovieRecord
    downloadRequestId: number
  }
}

export async function promoteRecommendations(
  sessionId: string,
  recommendationIds: string[],
): Promise<Array<{ movie: MovieRecord; downloadRequestId: number }>> {
  const response = await fetch(`${API_URL}/sessions/${sessionId}/promote-many`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recommendationIds }),
  })
  if (!response.ok) {
    throw await readError(response, 'Не удалось отправить фильмы на загрузку')
  }
  const body = (await response.json()) as {
    results: Array<{ movie: MovieRecord; downloadRequestId: number }>
  }
  return body.results
}
