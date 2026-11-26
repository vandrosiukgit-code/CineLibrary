const API_URL = '/api/agents/movie-librarian-1/library-import/jobs'
const MEDIA_SYNC_URL = '/api/agents/movie-librarian-1/media-sync'

export interface MediaSyncSettings {
  root: string
  excluded: string[]
}

export interface MediaFolders {
  path: string | null
  parent: string | null
  folders: Array<{ name: string; path: string }>
}

export async function browseMediaFolders(path: string | null): Promise<MediaFolders> {
  const query = path === null ? '' : `?${new URLSearchParams({ path })}`
  const response = await fetch(`${MEDIA_SYNC_URL}/folders${query}`)
  if (!response.ok) throw await readError(response, 'Не удалось открыть папку')
  return response.json()
}

export async function getMediaSyncSettings(): Promise<MediaSyncSettings> {
  const response = await fetch(`${MEDIA_SYNC_URL}/settings`)
  if (!response.ok) throw await readError(response, 'Не удалось открыть настройки медиатеки')
  return response.json()
}

export async function saveMediaSyncSettings(settings: MediaSyncSettings): Promise<MediaSyncSettings> {
  const response = await fetch(`${MEDIA_SYNC_URL}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
  if (!response.ok) throw await readError(response, 'Не удалось сохранить настройки медиатеки')
  return response.json()
}

export async function runMediaSync(): Promise<{ matched: number; pending: string[]; errors: Record<string, string> }> {
  const response = await fetch(MEDIA_SYNC_URL, { method: 'POST' })
  if (!response.ok) throw await readError(response, 'Не удалось синхронизировать медиатеку')
  return response.json()
}

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
