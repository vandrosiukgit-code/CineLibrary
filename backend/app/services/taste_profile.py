from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.repositories.movies import MovieRepository


class TasteProfileBuilder:
    """Builds an evidence-first profile that can be read directly by an LLM."""

    def __init__(self, repository: MovieRepository) -> None:
        self.repository = repository

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

        return {
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

    @staticmethod
    def _confidence(uses: int, total_movies: int) -> float:
        if total_movies <= 0:
            return 0.0
        return round(min(1.0, uses / max(3, total_movies * 0.15)), 2)
