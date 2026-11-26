const API_URL = '/api/people'

export interface PersonFilmographyItem {
  tmdbMovieId: number
  localMovieId: number | null
  creditKind: 'cast' | 'crew'
  title: string
  originalTitle: string
  releaseYear: number | null
  character: string | null
  department: string | null
  job: string | null
  posterUrl: string | null
  voteAverage: number | null
  inLibrary: boolean
}

export interface PersonRecord {
  id: number
  tmdbId: number
  name: string
  displayName: string
  alsoKnownAs: string[]
  biography: string
  birthday: string | null
  deathday: string | null
  placeOfBirth: string | null
  gender: number | null
  knownForDepartment: string | null
  profileUrl: string | null
  homepage: string | null
  imdbId: string | null
  wikidataId: string | null
  lastRefreshedAt: string
  nextRefreshAt: string
  filmography: PersonFilmographyItem[]
}

export async function loadPerson(
  personId: number,
  signal?: AbortSignal,
): Promise<PersonRecord> {
  const response = await fetch(`${API_URL}/${personId}`, { signal })
  if (!response.ok) throw new Error('Не удалось загрузить карточку человека')
  return (await response.json()) as PersonRecord
}
