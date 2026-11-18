from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.clients.replicate_gemini import ReplicateAPIError, ReplicateGeminiClient
from app.clients.tmdb import TMDBAPIError, TMDBClient
from app.repositories.movies import MovieRepository
from app.schemas.movie_research import (
    MovieIdentification,
    MovieLibrarianResult,
)
from app.services.movie_card_builder import MovieCardBuilder, MovieCardBuilderError


IDENTIFICATION_PROMPT = """
You are the identification brain of CineLibrary Movie Librarian 1.
Your only task is to determine which exact movie the user's text refers to.
The text may contain Russian or alternative translations, transliteration, a year,
director hints, or release-file noise.

You have three commands. Return exactly one JSON object and no Markdown on each turn.

Search command:
{"action":"search_tmdb_movie","arguments":{"query":"title","year":2021}}
Use null for an unknown year.

Candidate details command:
{"action":"get_tmdb_movie_candidate","arguments":{"tmdbId":123}}

Final command:
{"action":"submit_movie_identification","arguments":{"inputText":"exact user input","status":"identified|ambiguous|not_found","confidence":0.0,"tmdbId":null,"originalTitle":null,"releaseYear":null,"reason":"explanation","candidates":[]}}

Never identify a film from memory alone. Search TMDB, inspect candidates when
needed, and then submit identification. Select a movie
only when the evidence is unambiguous and confidence is at least 0.8. Otherwise
return ambiguous candidates or not_found. originalTitle must be the TMDB native
original_title, not an invented English translation. The selected tmdbId must come
from a tool result. For ambiguous results, candidates contain only objects with
tmdbId, originalTitle and releaseYear seen in tool results. Do not collect or
generate movie metadata.
""".strip()


class MovieLibrarianOutputError(RuntimeError):
    pass


class MovieLibrarian:
    MAX_TOOL_ROUNDS = 8

    def __init__(
        self,
        brain: ReplicateGeminiClient,
        tmdb: TMDBClient,
        repository: MovieRepository,
        builder: MovieCardBuilder | None = None,
    ) -> None:
        self.brain = brain
        self.tmdb = tmdb
        self.repository = repository
        self.builder = builder or MovieCardBuilder()

    def research_movies(self, movie_inputs: list[str]) -> list[MovieLibrarianResult]:
        results: list[MovieLibrarianResult] = []
        for movie_input in movie_inputs:
            try:
                results.append(self.research_movie(movie_input))
            except (ReplicateAPIError, TMDBAPIError, MovieLibrarianOutputError,
                    MovieCardBuilderError) as error:
                results.append(
                    MovieLibrarianResult(
                        inputText=movie_input,
                        status="failed",
                        identification=None,
                        movie=None,
                        existingMovieId=None,
                        sources=[],
                        issues=[str(error)],
                    )
                )
        return results

    def research_movie(self, movie_input: str) -> MovieLibrarianResult:
        identification = self.identify(movie_input)
        if identification.status != "identified":
            return MovieLibrarianResult(
                inputText=movie_input,
                status=identification.status,
                identification=identification,
                movie=None,
                existingMovieId=None,
                sources=[],
                issues=[identification.reason],
            )

        existing = self.repository.find_by_tmdb_id(identification.tmdb_id)
        if existing is not None:
            return MovieLibrarianResult(
                inputText=movie_input,
                status="already_exists",
                identification=identification,
                movie=None,
                existingMovieId=existing["id"],
                sources=[],
                issues=[],
            )

        card, sources = self.builder.build(
            self.tmdb.get_movie_bundle(identification.tmdb_id)
        )
        if card.tmdb_id != identification.tmdb_id:
            raise MovieCardBuilderError(
                "TMDB card ID does not match the identified movie"
            )
        return MovieLibrarianResult(
            inputText=movie_input,
            status="draft_ready",
            identification=identification,
            movie=card,
            existingMovieId=None,
            sources=sources,
            issues=[],
        )

    def identify(self, movie_input: str) -> MovieIdentification:
        history: list[dict[str, Any]] = []
        observed_tmdb_ids: set[int] = set()

        for _ in range(self.MAX_TOOL_ROUNDS):
            command = self.brain.next_action(
                IDENTIFICATION_PROMPT, movie_input, history
            )
            name = command.get("action")
            arguments = command.get("arguments")
            if not isinstance(arguments, dict):
                raise MovieLibrarianOutputError(
                    "Gemini command arguments must be an object"
                )

            if name == "submit_movie_identification":
                try:
                    identification = MovieIdentification.model_validate(arguments)
                except ValidationError as error:
                    raise MovieLibrarianOutputError(
                        "Gemini returned an invalid identification"
                    ) from error
                if identification.input_text != movie_input:
                    raise MovieLibrarianOutputError(
                        "Gemini changed the original movie input"
                    )
                if any(
                    candidate.tmdb_id not in observed_tmdb_ids
                    for candidate in identification.candidates
                ):
                    raise MovieLibrarianOutputError(
                        "Gemini returned a candidate not observed in TMDB tools"
                    )
                if (
                    identification.status == "identified"
                    and identification.tmdb_id not in observed_tmdb_ids
                ):
                    raise MovieLibrarianOutputError(
                        "Gemini selected a TMDB ID not returned by a tool"
                    )
                return identification

            if name == "search_tmdb_movie":
                query = arguments.get("query")
                year = arguments.get("year")
                if not isinstance(query, str) or not query.strip():
                    raise MovieLibrarianOutputError("Gemini provided an invalid query")
                if year is not None and not isinstance(year, int):
                    raise MovieLibrarianOutputError("Gemini provided an invalid year")
                result = self.tmdb.search_movie(query, year)
                observed_tmdb_ids.update(
                    item["tmdbId"] for item in result if item.get("tmdbId")
                )
            elif name == "get_tmdb_movie_candidate":
                tmdb_id = arguments.get("tmdbId")
                if not isinstance(tmdb_id, int) or tmdb_id <= 0:
                    raise MovieLibrarianOutputError("Gemini provided an invalid TMDB ID")
                result = self.tmdb.get_movie_candidate(tmdb_id)
                if result.get("tmdbId"):
                    observed_tmdb_ids.add(result["tmdbId"])
            else:
                raise MovieLibrarianOutputError(
                    f"Gemini requested an unsupported action: {name}"
                )

            history.append(
                {"action": name, "arguments": arguments, "result": result}
            )

        raise MovieLibrarianOutputError("Movie identification exceeded tool limit")

