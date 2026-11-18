
export type AvailabilityStatus =
  | 'available'
  | 'downloading'
  | 'missing'

export type PersonRole = 'actor' | 'director'

export interface Person {
  id: number
  name: string
  role: PersonRole
  personalRating: number | null
}

export interface Movie {
  id: number
  title: string
  originalTitle: string
  year: number

  // Жанр для совместимости с текущим интерфейсом
  genre: string
  genres: string[]

  rating: number
  poster: string
  overview: string

  directorId: number
  actorIds: number[]

  availability: AvailabilityStatus
  watched: boolean

  personalRating: number | null
  feedbackTags: string[]
  comment: string

  isNew: boolean
  inWishlist: boolean
}

// Общая база актёров и режиссёров.
// Оценка человека хранится только здесь.
export const people: Person[] = [
  {
    id: 1,
    name: 'Дени Вильнёв',
    role: 'director',
    personalRating: 5,
  },
  {
    id: 2,
    name: 'Ридли Скотт',
    role: 'director',
    personalRating: 4,
  },
  {
    id: 3,
    name: 'Кристофер Нолан',
    role: 'director',
    personalRating: 5,
  },
  {
    id: 4,
    name: 'Алекс Гарленд',
    role: 'director',
    personalRating: 4,
  },
  {
    id: 5,
    name: 'Райан Гослинг',
    role: 'actor',
    personalRating: 5,
  },
  {
    id: 6,
    name: 'Эми Адамс',
    role: 'actor',
    personalRating: 4,
  },
  {
    id: 7,
    name: 'Тимоти Шаламе',
    role: 'actor',
    personalRating: 4,
  },
  {
    id: 8,
    name: 'Мэттью Макконахи',
    role: 'actor',
    personalRating: 5,
  },
  {
    id: 9,
    name: 'Алисия Викандер',
    role: 'actor',
    personalRating: 4,
  },
]

// Эмулированная база фильмов
export const movies: Movie[] = [
  {
    id: 1,
    title: 'Бегущий по лезвию 2049',
    originalTitle: 'Blade Runner 2049',
    year: 2017,
    genre: 'Фантастика',
    genres: ['Фантастика', 'Драма', 'Триллер'],
    rating: 8.0,
    poster:
      'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg',
    overview:
      'Молодой офицер полиции раскрывает тайну, способную изменить представление человечества о собственном существовании.',
    directorId: 1,
    actorIds: [5],
    availability: 'available',
    watched: true,
    personalRating: 5,
    feedbackTags: ['Хорошая атмосфера', 'Оригинальная идея'],
    comment: '',
    isNew: false,
    inWishlist: false,
  },
  {
    id: 2,
    title: 'Прибытие',
    originalTitle: 'Arrival',
    year: 2016,
    genre: 'Фантастика',
    genres: ['Фантастика', 'Драма', 'Детектив'],
    rating: 7.9,
    poster:
      'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg',
    overview:
      'Лингвист пытается установить контакт с инопланетной цивилизацией, прибывшей на Землю.',
    directorId: 1,
    actorIds: [6],
    availability: 'available',
    watched: true,
    personalRating: 5,
    feedbackTags: ['Интересный сюжет', 'Эмоциональная глубина'],
    comment: '',
    isNew: false,
    inWishlist: false,
  },
  {
    id: 3,
    title: 'Дюна',
    originalTitle: 'Dune',
    year: 2021,
    genre: 'Фантастика',
    genres: ['Фантастика', 'Приключения', 'Драма'],
    rating: 8.0,
    poster:
      'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg',
    overview:
      'История Пола Атрейдеса и его путешествия на пустынную планету Арракис.',
    directorId: 1,
    actorIds: [7],
    availability: 'downloading',
    watched: false,
    personalRating: null,
    feedbackTags: [],
    comment: '',
    isNew: false,
    inWishlist: true,
  },
  {
    id: 4,
    title: 'Из машины',
    originalTitle: 'Ex Machina',
    year: 2014,
    genre: 'Фантастика',
    genres: ['Фантастика', 'Триллер', 'Драма'],
    rating: 7.7,
    poster:
      'https://image.tmdb.org/t/p/w500/dmJW8IAKHKxFNiUnoDR7JfsK7Rp.jpg',
    overview:
      'Программист участвует в эксперименте по проверке возможностей искусственного интеллекта.',
    directorId: 4,
    actorIds: [9],
    availability: 'missing',
    watched: false,
    personalRating: null,
    feedbackTags: [],
    comment: '',
    isNew: true,
    inWishlist: true,
  },
  {
    id: 5,
    title: 'Интерстеллар',
    originalTitle: 'Interstellar',
    year: 2014,
    genre: 'Фантастика',
    genres: ['Фантастика', 'Приключения', 'Драма'],
    rating: 8.7,
    poster:
      'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg',
    overview:
      'Группа исследователей отправляется через червоточину на поиски нового дома для человечества.',
    directorId: 3,
    actorIds: [8],
    availability: 'available',
    watched: true,
    personalRating: 5,
    feedbackTags: ['Интересный сюжет', 'Эмоциональная глубина'],
    comment: '',
    isNew: true,
    inWishlist: false,
  },
]
