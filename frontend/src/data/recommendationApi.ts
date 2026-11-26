const API_URL = 'http://127.0.0.1:8000/api/agents/movie-recommender'

export interface ConfiguratorAnswer {
  cardId: string
  title: string
  values: string[]
  skipped: boolean
}

export interface ReferenceMovie {
  tmdbId: number
  relation: 'similar' | 'avoid'
}

export interface SuggestedMovie {
  title: string
  originalTitle: string | null
  releaseYear: number | null
  relevance: number
  reason: string
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
  tmdbId?: number | null
  suggestion: SuggestedMovie
  status: 'draft_ready' | 'already_exists' | 'ambiguous' | 'not_found' | 'failed'
  movie: TemporaryMovieCard | null
  existingMovieId: number | null
  people: TemporaryPerson[]
  issues: string[]
  scoreExplanation?: string | null
  canRequestDownload?: boolean
  breakdown?: {
    chefPick: boolean
    wishScore: number | null
    referenceScore: number | null
    matches: Array<{ label: string; score: number | null; detail: string }>
    summary: string
  } | null
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
  references: ReferenceMovie[] = [],
): Promise<RecommendationJob> {
  const response = await fetch(`${API_URL}/recommend/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, count, references }),
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
