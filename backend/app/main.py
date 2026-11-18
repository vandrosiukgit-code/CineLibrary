from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.movie_librarian import router as movie_librarian_router
from app.api.routes.movies import router as movies_router
from app.database import MovieDatabase
from app.repositories.movies import MovieRepository


def create_app(database_path: Path | str | None = None) -> FastAPI:
    database = MovieDatabase(database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database.initialize()
        application.state.movie_repository = MovieRepository(database)
        yield

    application = FastAPI(
        title="CineLibrary",
        description="Personal Cinematic Knowledge Management System",
        version="0.2.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(movies_router)
    application.include_router(movie_librarian_router)

    @application.get("/")
    def root():
        return {
            "application": "CineLibrary",
            "version": "0.2.0",
            "status": "running",
        }

    @application.get("/api/health")
    def health():
        return {"status": "healthy"}

    return application


app = create_app()
