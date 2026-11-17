export interface Movie {
  id: number
  title: string
  originalTitle: string
  year: number
  genre: string
  rating: number
  poster: string
}

export const movies: Movie[] = [
  {
    id: 1,
    title: 'Бегущий по лезвию 2049',
    originalTitle: 'Blade Runner 2049',
    year: 2017,
    genre: 'Фантастика',
    rating: 8.0,
    poster: 'https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg',
  },
  {
    id: 2,
    title: 'Прибытие',
    originalTitle: 'Arrival',
    year: 2016,
    genre: 'Фантастика',
    rating: 7.9,
    poster: 'https://image.tmdb.org/t/p/w500/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg',
  },
  {
    id: 3,
    title: 'Дюна',
    originalTitle: 'Dune',
    year: 2021,
    genre: 'Фантастика',
    rating: 8.0,
    poster: 'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg',
  },
  {
    id: 4,
    title: 'Из машины',
    originalTitle: 'Ex Machina',
    year: 2014,
    genre: 'Фантастика',
    rating: 7.7,
    poster: 'https://image.tmdb.org/t/p/w500/dmJW8IAKHKxFNiUnoDR7JfsK7Rp.jpg',
  },
  {
    id: 5,
    title: 'Интерстеллар',
    originalTitle: 'Interstellar',
    year: 2014,
    genre: 'Фантастика',
    rating: 8.7,
    poster: 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg',
  },
]