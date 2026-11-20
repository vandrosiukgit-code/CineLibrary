from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TMDBConfigurationError(RuntimeError):
    pass


class TMDBAPIError(RuntimeError):
    pass


Transport = Callable[[str, dict[str, str], float], dict[str, Any]]


def _default_transport(
    url: str, headers: dict[str, str], timeout: float
) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise TMDBAPIError(f"TMDB API returned HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise TMDBAPIError("TMDB API request failed") from error


class TMDBClient:
    def __init__(
        self,
        read_access_token: str,
        *,
        base_url: str = "https://api.themoviedb.org/3",
        timeout: float = 30,
        transport: Transport = _default_transport,
    ) -> None:
        if not read_access_token.strip():
            raise TMDBConfigurationError("TMDB_READ_ACCESS_TOKEN is not configured")
        self.read_access_token = read_access_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    @classmethod
    def from_environment(cls) -> "TMDBClient":
        return cls(
            os.getenv("TMDB_READ_ACCESS_TOKEN", ""),
            base_url=os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3"),
            timeout=float(os.getenv("TMDB_TIMEOUT_SECONDS", "30")),
        )

    def search_movie(self, query: str, year: int | None = None) -> list[dict[str, Any]]:
        parameters: dict[str, Any] = {
            "query": query,
            "language": "ru-RU",
            "include_adult": "false",
        }
        if year is not None:
            parameters["year"] = year
        response = self._get("/search/movie", parameters)
        return [self._candidate(item) for item in response.get("results", [])[:10]]

    def get_movie_candidate(self, tmdb_id: int) -> dict[str, Any]:
        return self._candidate(
            self._get(f"/movie/{tmdb_id}", {"language": "ru-RU"})
        )

    def get_movie_bundle(self, tmdb_id: int) -> dict[str, Any]:
        localized = self._get(
            f"/movie/{tmdb_id}",
            {
                "language": "ru-RU",
                "append_to_response": "credits,external_ids,release_dates",
            },
        )
        english = self._get(f"/movie/{tmdb_id}", {"language": "en-US"})
        return {"localized": localized, "english": english}

    def get_movie_credits(self, tmdb_id: int) -> dict[str, Any]:
        return self._get(f"/movie/{tmdb_id}/credits", {"language": "ru-RU"})

    def get_person_bundle(self, person_id: int) -> dict[str, Any]:
        return self._get(
            f"/person/{person_id}",
            {
                "language": "ru-RU",
                "append_to_response": "external_ids,movie_credits,translations",
            },
        )

    def _get(self, path: str, parameters: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode(parameters)}"
        return self.transport(
            url,
            {
                "Authorization": f"Bearer {self.read_access_token}",
                "Accept": "application/json",
            },
            self.timeout,
        )

    @staticmethod
    def _candidate(item: dict[str, Any]) -> dict[str, Any]:
        release_date = item.get("release_date") or ""
        return {
            "tmdbId": item.get("id"),
            "title": item.get("title"),
            "originalTitle": item.get("original_title"),
            "originalLanguage": item.get("original_language"),
            "releaseYear": int(release_date[:4]) if len(release_date) >= 4 else None,
            "overview": item.get("overview") or None,
        }
