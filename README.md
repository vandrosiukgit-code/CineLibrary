# CineLibrary

Personal Cinematic Knowledge Management System.

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

The backend creates `data\movies.db` automatically on first startup. The
database schema and the reproducible five-movie test dataset are stored in:

    backend\app\sql\001_initial_schema.sql
    backend\app\sql\test_seed.sql

Available API operations:

    GET /api/movies
    GET /api/movies/{movie_id}
    PATCH /api/movies/{movie_id}/user-data

The list endpoint supports `search`, `watched`, `inWishlist`, `availability`
and `genre` query parameters.

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

People Database, draft approval/import and a separate IMDb-rating source are not
connected yet.
