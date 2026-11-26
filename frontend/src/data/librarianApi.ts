const API_URL = 'http://127.0.0.1:8000/api/agents/movie-librarian-1/library-import/jobs'

export interface LibraryImportLog {
  sequence: number
  createdAt: string
  message: string
}

export interface LibraryImportItem {
  inputText: string
  status: 'imported' | 'updated' | 'ambiguous' | 'not_found' | 'failed'
  movieId: number | null
  title: string | null
  issues: string[]
  candidates: LibraryImportCandidate[]
}

export interface LibraryImportCandidate {
  tmdbId: number
  originalTitle: string
  releaseYear: number | null
}

export interface LibraryImportJob {
  jobId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  logs: LibraryImportLog[]
  result: { items: LibraryImportItem[] } | null
  error: string | null
}

async function readError(response: Response, fallback: string) {
  const body = (await response.json().catch(() => null)) as
    | { detail?: string }
    | null
  return new Error(body?.detail || fallback)
}

export async function startLibraryImport(text: string): Promise<LibraryImportJob> {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  if (!response.ok) throw await readError(response, 'Не удалось запустить добавление фильмов')
  return (await response.json()) as LibraryImportJob
}

export async function startCandidateLibraryImport(
  tmdbIds: number[],
): Promise<LibraryImportJob> {
  const response = await fetch(`${API_URL}/candidates/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tmdbIds }),
  })
  if (!response.ok) throw await readError(response, 'Не удалось запустить добавление выбранных фильмов')
  return (await response.json()) as LibraryImportJob
}

export async function loadLibraryImport(jobId: string): Promise<LibraryImportJob> {
  const response = await fetch(`${API_URL}/${jobId}`)
  if (!response.ok) throw await readError(response, 'Не удалось получить состояние импорта')
  return (await response.json()) as LibraryImportJob
}

export async function cancelLibraryImport(jobId: string): Promise<LibraryImportJob> {
  const response = await fetch(`${API_URL}/${jobId}/cancel`, { method: 'POST' })
  if (!response.ok) throw await readError(response, 'Не удалось остановить импорт')
  return (await response.json()) as LibraryImportJob
}
