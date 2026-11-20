from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.movie_librarian import router as movie_librarian_router
from app.api.routes.movie_recommender import router as movie_recommender_router
from app.api.routes.movies import router as movies_router
from app.api.routes.people import router as people_router
from app.api.routes.settings import router as settings_router
from app.database import MovieDatabase
from app.repositories.movies import MovieRepository
from app.repositories.people import PeopleRepository
from app.repositories.recommendation_sessions import RecommendationSessionStore
from app.services.recommendation_jobs import RecommendationJobManager
from app.services.telegram_delivery import TelegramDeliveryService
from app.services.api_credentials import APICredentialsService


def create_app(
    database_path: Path | str | None = None,
    seed_path: Path | str | None = None,
) -> FastAPI:
    database = MovieDatabase(database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database.initialize()
        if seed_path is not None:
            database.seed(seed_path)
        application.state.movie_repository = MovieRepository(database)
        application.state.people_repository = PeopleRepository(database)
        application.state.recommendation_sessions = RecommendationSessionStore()
        application.state.recommendation_jobs = RecommendationJobManager()
        application.state.telegram_delivery = TelegramDeliveryService(database)
        application.state.api_credentials = APICredentialsService(database)
        application.state.api_credentials.apply_saved_credentials()
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
    application.include_router(movie_recommender_router)
    application.include_router(people_router)
    application.include_router(settings_router)

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
