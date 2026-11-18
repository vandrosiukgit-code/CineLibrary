export type AvailabilityStatus = 'available' | 'downloading' | 'missing'

export type CreditType =
  | 'director'
  | 'writer'
  | 'cinematographer'
  | 'composer'
  | 'actor'
  | 'producer'
  | 'editor'
  | 'production_designer'
  | 'other'

export interface MovieCredit {
  id: number
  personId: number | null
  canonicalName: string
  displayName: string
  creditType: CreditType
  sortOrder: number
}

export interface MovieGenre {
  id: number
  canonicalName: string
  displayName: string
}

export interface MovieUserData {
  watched: boolean
  personalRating: number | null
  comment: string
  inWishlist: boolean
  tags: string[]
}

export interface MovieRecord {
  id: number
  title: string
  originalTitle: string
  releaseYear: number
  tmdbId: number | null
  imdbId: string | null
  runtimeMinutes: number | null
  originalLanguage: string | null
  overview: string
  posterUrl: string | null
  certificationCountry: string | null
  certificationRating: string | null
  imdbRating: number | null
  isNew: boolean
  genres: MovieGenre[]
  credits: MovieCredit[]
  productionCompanies: string[]
  availability: AvailabilityStatus
  userData: MovieUserData
}

export interface MovieUserDataUpdate {
  watched?: boolean
  personalRating?: number | null
  comment?: string
  inWishlist?: boolean
}
