import './App.css'
import { movies } from './data/movies'
const menuItems = [
  { icon: '⌂', label: 'Главная' },
  { icon: '▤', label: 'Моя библиотека' },
  { icon: '✓', label: 'Просмотренные' },
  { icon: '◷', label: 'Смотреть позже' },
  { icon: '▦', label: 'Коллекции' },
  { icon: '◇', label: 'Жанры' },
  { icon: '✧', label: 'Рекомендации' },
]

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">C</div>
          <span>CineLibrary</span>
        </div>

        <div className="sidebar-label">МЕНЮ</div>

        <nav className="navigation">
          {menuItems.map((item, index) => (
            <button
              className={`nav-item ${index === 0 ? 'active' : ''}`}
              key={item.label}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span className="nav-icon">⚙</span>
            <span>Настройки</span>
          </button>
          <div className="sidebar-version">CineLibrary · версия 0.1</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">Моя коллекция / Главная</div>
          <div className="profile">
            <div className="profile-avatar">U</div>
          </div>
        </header>

        <section className="welcome-section">
          <div>
            <div className="eyebrow">ВАША ЛИЧНАЯ КИНОТЕКА</div>
            <h1>Добро пожаловать</h1>
            <p>Ваша история кино начинается здесь.</p>
          </div>

          <button className="add-button">＋ Добавить фильм</button>
        </section>

        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">Всего фильмов</div>
            <div className="stat-value">1 248</div>
            <div className="stat-note">В вашей библиотеке</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Просмотрено</div>
            <div className="stat-value">836</div>
            <div className="stat-note">Фильмов просмотрено</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Смотреть позже</div>
            <div className="stat-value">124</div>
            <div className="stat-note">В вашем списке</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">Коллекции</div>
            <div className="stat-value">18</div>
            <div className="stat-note">Тематических подборок</div>
          </div>
        </section>

        <section className="content-section">
          <div className="section-heading">
            <div>
              <h2>Продолжить знакомство</h2>
              <p>Фильмы, которые могут вас заинтересовать</p>
            </div>
            <button className="text-button">Вся библиотека →</button>
          </div>

<div className="movie-grid">
  {movies.map((movie) => (
    <article className="movie-card" key={movie.id}>
      <div className="movie-poster">
        <img src={movie.poster} alt={movie.title} />
        <div className="movie-rating">★ {movie.rating}</div>
      </div>

      <div className="movie-info">
        <h3>{movie.title}</h3>
        <p>{movie.year} · {movie.genre}</p>
      </div>
    </article>
  ))}
</div>
      </section>
    </main>
  </div>
  )
}

export default App