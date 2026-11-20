# CineLibrary

Personal Cinematic Knowledge Management System.

## Быстрый запуск

Откройте два окна PowerShell.

В первом окне запустите backend:

```powershell
cd D:\КИНО\CineLibrary
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload
```

Во втором окне запустите frontend:

```powershell
cd D:\КИНО\CineLibrary\frontend
npm run dev
```

Откройте приложение: http://localhost:5173

Документация API: http://127.0.0.1:8000/docs

Для остановки сервера нажмите `Ctrl+C` в соответствующем окне.

## Project location

D:\КИНО\CineLibrary

## Backend setup

Open the project in PyCharm Professional.

Create a Python virtual environment in the project root:

    python -m venv .venv

Activate it in PowerShell:

    .\.venv\Scripts\Activate.ps1

Install dependencies:

    pip install -r backend\requirements.txt

Run the backend from the backend directory:

    uvicorn app.main:app --reload

Backend:
http://127.0.0.1:8000

API documentation:
http://127.0.0.1:8000/docs

## Movie Database

The backend creates an empty `data\movies.db` automatically on first startup.
Database migrations are stored in:

    backend\app\sql\001_initial_schema.sql
    backend\app\sql\002_add_tmdb_rating.sql

The reproducible five-movie demo dataset is used only by tests and is stored in:

    backend\tests\fixtures\demo_movie_catalog.sql

Local SQLite files are ignored by Git. `data\movies-demo.db` is a recoverable
backup of the former demo catalog; `data\movies.db` is the real catalog.

Available API operations:

    GET /api/movies
    GET /api/movies/{movie_id}
    POST /api/movies/import
    PATCH /api/movies/{movie_id}/user-data
    GET /api/people/{person_id}
    POST /api/people/sync
    POST /api/agents/movie-recommender/recommend
    POST /api/agents/movie-recommender/recommend/jobs
    GET /api/agents/movie-recommender/recommend/jobs/{job_id}
    POST /api/agents/movie-recommender/recommend/jobs/{job_id}/cancel
    POST /api/agents/movie-recommender/sessions/{session_id}/promote
    POST /api/agents/movie-recommender/sessions/{session_id}/promote-many
    POST /api/movies/download-requests/by-tmdb
    GET /api/movies/telegram-settings
    PUT /api/movies/telegram-settings
    POST /api/movies/telegram-settings/test

The list endpoint supports `search`, `watched`, `inWishlist`, `availability`
and `genre` query parameters.

The recommender rebuilds an evidence-based taste profile from watched movies on
every request, combines it with configurator answers and asks Gemini for an exact
number of recommendations. Movie Librarian 1 resolves every recommendation and
builds full TMDB cards in a process-local temporary catalog. Temporary sessions
expire after 24 hours. Promoting a recommendation imports it with
`watched=false`, marks it as downloading, creates a download request and
synchronizes its people records.

Recommendations selected from the temporary catalog are processed together and
sent to the configured Telegram chat in one message. A film selected from a
person's filmography uses the same TMDB import, people synchronization and
Telegram pipeline. Each entry contains the movie's international title and a filesystem-safe name in the form
`CL-000123_International_Title`; the numeric prefix is the permanent movie-card
ID. Configure the bot token and Chat ID from the restored left sidebar. The token
is stored locally in the application database and is never returned by the API.

The frontend uses recommendation jobs so it can show an ordered process log and
request cooperative cancellation. Cancellation takes effect at the next safe
checkpoint; an already running Replicate or TMDB HTTP request is allowed to finish.

## Frontend

Install dependencies and start Vite:

    cd frontend
    npm install
    npm run dev

The frontend loads movies from `http://127.0.0.1:8000`, supports title search,
library filters, and editing watched, wishlist and personal rating fields.

## Movie Librarian 1

Movie Librarian 1 accepts a natural-language movie list. Gemini 3 Flash, accessed
through Replicate, identifies the exact film by requesting TMDB search tools.
Python executes those tools, checks the local database and,
for a new TMDB ID, builds a validated draft only from TMDB API responses. The agent
does not write drafts directly to Movie Database.

Set both API credentials in the PowerShell window before starting the backend:

    $env:REPLICATE_API_TOKEN = Read-Host "Replicate API token"
    $env:REPLICATE_MODEL = "google/gemini-3-flash"
    $env:GEMINI_THINKING_LEVEL = "low"
    $env:TMDB_READ_ACCESS_TOKEN = Read-Host "TMDB Read Access Token"
    cd backend
    uvicorn app.main:app --reload

Research endpoint:

    POST /api/agents/movie-librarian-1/research

Example body:

    {
      "movies": ["Arrival (2016)", "Дюна 2021"]
    }

The agent keeps the native TMDB `original_title`, uses the Russian TMDB title for
display and collects text credits only for actors, directors, producers, writers
and composers. Every credit has `personId: null`; People Database records are
outside this agent's responsibilities. TMDB rating is stored separately;
`imdbRating` stays null because TMDB is not a source for IMDb ratings.

## Current limitations

Draft approval/import and a separate IMDb-rating source are not connected yet.

## People catalog

Movie imports start a background TMDB synchronization for their key cast and crew.
Person cards store a profile photo, biography, external IDs, movie credits and the
date of the last successful refresh. Fresh cards are reused; cards older than six
calendar months are replaced from TMDB. Movie-person links are updated on every
sync, even when the person card itself is still fresh.

Run a full catalog synchronization with:

    POST /api/people/sync

Or synchronize one movie after a metadata update:

    POST /api/people/sync?movieId=1
