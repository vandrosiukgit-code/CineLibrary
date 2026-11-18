from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import ValidationError

from app.schemas.movie_research import (
    CertificationDraft,
    LocalizedName,
    MovieCardDraft,
    MovieCreditDraft,
    MovieSourceDraft,
)


class MovieCardBuilderError(RuntimeError):
    pass


class MovieCardBuilder:
    WRITER_JOBS = {"Screenplay", "Writer", "Story"}
    COMPOSER_JOBS = {"Original Music Composer", "Music"}

    def build(
        self, bundle: dict[str, Any]
    ) -> tuple[MovieCardDraft, list[MovieSourceDraft]]:
        localized = bundle["localized"]
        english = bundle["english"]
        release_date = localized.get("release_date") or english.get("release_date") or ""
        if not localized.get("id") or len(release_date) < 4:
            raise MovieCardBuilderError("TMDB returned incomplete movie identity")

        tmdb_id = int(localized["id"])
        try:
            card = MovieCardDraft(
                title=(
                    localized.get("title")
                    or localized.get("original_title")
                    or english.get("title")
                ),
                originalTitle=(
                    localized.get("original_title") or english.get("original_title")
                ),
                releaseYear=int(release_date[:4]),
                tmdbId=tmdb_id,
                imdbId=(localized.get("external_ids") or {}).get("imdb_id"),
                runtimeMinutes=localized.get("runtime") or english.get("runtime"),
                countries=[
                    country["name"]
                    for country in english.get("production_countries", [])
                    if country.get("name")
                ],
                originalLanguage=localized.get("original_language"),
                certification=self._certification(localized.get("release_dates") or {}),
                genres=self._genres(localized, english),
                overview=localized.get("overview") or english.get("overview") or None,
                credits=self._credits(localized.get("credits") or {}),
                productionCompanies=[
                    company["name"]
                    for company in localized.get("production_companies", [])
                    if company.get("name")
                ],
                tmdbRating=self._rating(localized),
                imdbRating=None,
                posterUrl=self._poster_url(
                    localized.get("poster_path") or english.get("poster_path")
                ),
            )
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise MovieCardBuilderError("TMDB data failed card validation") from error

        source = MovieSourceDraft(
            sourceName="TMDB",
            sourceUrl=f"https://www.themoviedb.org/movie/{tmdb_id}",
            checkedAt=date.today(),
            supportedFields=[
                "title",
                "originalTitle",
                "releaseYear",
                "tmdbId",
                "imdbId",
                "runtimeMinutes",
                "countries",
                "originalLanguage",
                "certification",
                "genres",
                "overview",
                "credits",
                "productionCompanies",
                "tmdbRating",
                "posterUrl",
            ],
        )
        return card, [source]

    @staticmethod
    def _genres(
        localized: dict[str, Any], english: dict[str, Any]
    ) -> list[LocalizedName]:
        english_by_id = {
            genre["id"]: genre["name"]
            for genre in english.get("genres", [])
            if genre.get("id") and genre.get("name")
        }
        return [
            LocalizedName(
                canonicalName=english_by_id.get(genre.get("id"), genre["name"]),
                displayName=genre["name"],
            )
            for genre in localized.get("genres", [])
            if genre.get("name")
        ]

    def _credits(self, credits: dict[str, Any]) -> list[MovieCreditDraft]:
        result: list[MovieCreditDraft] = []
        seen: set[tuple[str, str]] = set()

        actors = sorted(credits.get("cast", []), key=lambda item: item.get("order", 9999))
        for order, person in enumerate(actors[:10]):
            self._append_credit(result, seen, person, "actor", order)

        role_jobs = {
            "director": {"Director"},
            "producer": {"Producer"},
            "writer": self.WRITER_JOBS,
            "composer": self.COMPOSER_JOBS,
        }
        crew = credits.get("crew", [])
        for role, jobs in role_jobs.items():
            role_order = 0
            for person in crew:
                if person.get("job") not in jobs:
                    continue
                if self._append_credit(result, seen, person, role, role_order):
                    role_order += 1
        return result

    @staticmethod
    def _append_credit(
        result: list[MovieCreditDraft],
        seen: set[tuple[str, str]],
        person: dict[str, Any],
        role: str,
        order: int,
    ) -> bool:
        name = person.get("name") or person.get("original_name")
        if not name:
            return False
        key = (name.casefold(), role)
        if key in seen:
            return False
        seen.add(key)
        result.append(
            MovieCreditDraft(
                canonicalName=name,
                displayName=name,
                creditType=role,
                sortOrder=order,
                personId=None,
            )
        )
        return True

    @staticmethod
    def _certification(release_dates: dict[str, Any]) -> CertificationDraft | None:
        by_country = {
            item.get("iso_3166_1"): item.get("release_dates", [])
            for item in release_dates.get("results", [])
        }
        for country in ("UA", "US"):
            for release in by_country.get(country, []):
                rating = (release.get("certification") or "").strip()
                if rating:
                    return CertificationDraft(country=country, rating=rating)
        return None

    @staticmethod
    def _rating(movie: dict[str, Any]) -> float | None:
        rating = movie.get("vote_average")
        return float(rating) if rating is not None else None

    @staticmethod
    def _poster_url(path: str | None) -> str | None:
        return f"https://image.tmdb.org/t/p/w500{path}" if path else None
