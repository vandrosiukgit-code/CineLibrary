from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.repositories.movies import MovieRepository
from app.services.movie_dna import MovieDNAService


class TasteProfileBuilder:
    """Builds an evidence-first profile that can be read directly by an LLM."""

    def __init__(
        self, repository: MovieRepository, *, movie_dna: MovieDNAService | None = None
    ) -> None:
        self.repository = repository
        self.movie_dna = movie_dna

    def build(self) -> dict[str, Any]:
        movies = self.repository.list_movies(watched=True, sort="release_desc")
        tag_definitions = {
            tag["code"]: tag for tag in self.repository.list_taste_tags()
        }
        tag_stats: dict[str, dict[str, Any]] = {}
        genre_ratings: dict[str, list[int]] = defaultdict(list)
        evidence: list[dict[str, Any]] = []
        do_not_recommend: list[dict[str, Any]] = []

        for movie in movies:
            user_data = movie["user_data"]
            rating = user_data["personal_rating"]
            do_not_recommend.append(
                {
                    "tmdbId": movie.get("tmdb_id"),
                    "title": movie["title"],
                    "originalTitle": movie["original_title"],
                    "releaseYear": movie["release_year"],
                }
            )
            if rating is not None:
                for genre in movie["genres"]:
                    genre_ratings[genre["display_name"]].append(rating)
            for code, label in zip(
                user_data["tag_codes"], user_data["tags"], strict=False
            ):
                stat = tag_stats.setdefault(
                    code,
                    {
                        "code": code,
                        "label": label,
                        "sentiment": tag_definitions.get(code, {}).get(
                            "sentiment", 0
                        ),
                        "uses": 0,
                        "ratings": [],
                    },
                )
                stat["uses"] += 1
                if rating is not None:
                    stat["ratings"].append(rating)

            if (
                rating is not None
                or user_data["tag_codes"]
                or user_data["comment"].strip()
            ):
                evidence.append(
                    {
                        "tmdbId": movie.get("tmdb_id"),
                        "title": movie["title"],
                        "releaseYear": movie["release_year"],
                        "ratingOutOf5": rating,
                        "genres": [
                            genre["display_name"] for genre in movie["genres"]
                        ],
                        "tags": user_data["tag_codes"],
                        "comment": user_data["comment"] or None,
                    }
                )

        signals = []
        for stat in tag_stats.values():
            ratings = stat.pop("ratings")
            signals.append(
                {
                    **stat,
                    "averageRatingOutOf5": (
                        round(sum(ratings) / len(ratings), 2) if ratings else None
                    ),
                    "confidence": self._confidence(stat["uses"], len(movies)),
                }
            )
        signals.sort(key=lambda item: (-item["uses"], item["code"]))

        genres = [
            {
                "name": name,
                "ratedMovies": len(ratings),
                "averageRatingOutOf5": round(sum(ratings) / len(ratings), 2),
                "confidence": self._confidence(len(ratings), len(movies)),
            }
            for name, ratings in genre_ratings.items()
        ]
        genres.sort(
            key=lambda item: (
                -item["averageRatingOutOf5"],
                -item["ratedMovies"],
                item["name"],
            )
        )

        profile = {
            "format": "cinelibrary.taste-profile.v1",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "interpretationRules": [
                "This is a movie preference profile, not a psychological diagnosis.",
                "Prefer repeated evidence over a single rating or tag.",
                "Low confidence signals are weak hints, not hard constraints.",
                "Never recommend a movie listed in doNotRecommend.",
            ],
            "summary": {
                "watchedMovies": len(movies),
                "ratedMovies": sum(
                    movie["user_data"]["personal_rating"] is not None
                    for movie in movies
                ),
                "moviesWithTasteTags": sum(
                    bool(movie["user_data"]["tag_codes"]) for movie in movies
                ),
            },
            "genreSignals": genres,
            "tagSignals": signals,
            "movieEvidence": evidence,
            "doNotRecommend": do_not_recommend,
        }
        dna_signals = self._movie_dna_signals(movies)
        if dna_signals is not None:
            profile["movieDNASignals"] = dna_signals
        return profile

    def _movie_dna_signals(
        self, movies: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        if self.movie_dna is None:
            return None

        tag_signals: dict[int, dict[str, Any]] = {}
        viewing_context: dict[int, dict[str, Any]] = {}
        source_counts = {"original": 0, "estimated": 0}
        for movie in movies:
            rating = movie["user_data"]["personal_rating"]
            tmdb_id = movie.get("tmdb_id")
            if tmdb_id is None or tmdb_id <= 0:
                continue
            genome = self.movie_dna.get(tmdb_id)
            source = genome.get("source")
            if genome["status"] != "found" or source not in source_counts:
                continue
            strongest_tags = sorted(
                genome["tags"], key=lambda tag: (-tag["relevance"], tag["tag_id"])
            )[:12]
            source_weight = 0.5 if source == "estimated" else 1.0
            # Three stars and absent ratings contribute only to viewing context.
            weight = (rating - 3) * source_weight if rating is not None else 0.0
            if weight:
                source_counts[source] += 1
            count_key = "highRatedMovies" if weight > 0 else "lowRatedMovies"
            for tag in strongest_tags:
                relevance = tag["relevance"]
                if relevance <= 0:
                    continue
                if not weight:
                    context = viewing_context.setdefault(
                        tag["tag_id"], {"name": tag["name"], "score": 0.0, "movies": 0}
                    )
                    context["score"] += source_weight * relevance
                    context["movies"] += 1
                    continue
                signal = tag_signals.setdefault(
                    tag["tag_id"],
                    {
                        "name": tag["name"],
                        "score": 0.0,
                        "highRatedMovies": 0,
                        "lowRatedMovies": 0,
                    },
                )
                signal["score"] += weight * relevance
                signal[count_key] += 1

        if not tag_signals and not viewing_context:
            return None
        ranked = sorted(
            tag_signals.values(),
            key=lambda signal: (-abs(signal["score"]), signal["name"]),
        )
        higher, lower = [], []
        for signal in ranked:
            score = round(signal["score"], 3)
            if score:
                (higher if score > 0 else lower).append({**signal, "score": score})
        frequent_context = sorted(
            viewing_context.values(),
            key=lambda tag: (-tag["score"], tag["name"]),
        )[:8]
        return {
            "ratedMoviesWithOriginal": source_counts["original"],
            "ratedMoviesWithEstimated": source_counts["estimated"],
            "associatedWithHigherRatings": higher[:8],
            "associatedWithLowerRatings": lower[:8],
            "viewingContext": [
                {"name": tag["name"], "movies": tag["movies"]} for tag in frequent_context
            ],
        }

    @staticmethod
    def _confidence(uses: int, total_movies: int) -> float:
        if total_movies <= 0:
            return 0.0
        return round(min(1.0, uses / max(3, total_movies * 0.15)), 2)
