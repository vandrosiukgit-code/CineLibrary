from __future__ import annotations

from typing import Any

from app.clients.tmdb import TMDBAPIError, TMDBClient
from app.repositories.people import PeopleRepository


class PeopleSynchronizer:
    WRITER_JOBS = {"Screenplay", "Writer", "Story"}
    COMPOSER_JOBS = {"Original Music Composer", "Music"}

    def __init__(self, tmdb: TMDBClient, repository: PeopleRepository) -> None:
        self.tmdb = tmdb
        self.repository = repository

    def sync_all(self) -> dict[str, Any]:
        summary = self._empty_summary()
        for movie in self.repository.list_movie_targets():
            self._merge(summary, self.sync_movie(movie["id"], movie["tmdb_id"]))
        return summary

    def sync_movie(self, movie_id: int, tmdb_id: int) -> dict[str, Any]:
        summary = self._empty_summary()
        try:
            credits = self.tmdb.get_movie_credits(tmdb_id)
        except TMDBAPIError as error:
            summary["failures"].append(f"Movie {tmdb_id}: {error}")
            return summary

        summary["movies_processed"] = 1
        for credit in self.selected_credits(credits):
            tmdb_person_id = credit["tmdb_person_id"]
            person = self.repository.find_by_tmdb_id(tmdb_person_id)
            if person is None or self.repository.refresh_is_due(person):
                try:
                    bundle = self.tmdb.get_person_bundle(tmdb_person_id)
                    person_id, created = self.repository.upsert_person(bundle)
                except (TMDBAPIError, KeyError, TypeError, ValueError) as error:
                    summary["failures"].append(
                        f"Person {tmdb_person_id}: {error}"
                    )
                    continue
                key = "people_created" if created else "people_refreshed"
                summary[key] += 1
            else:
                person_id = person["id"]
                summary["people_skipped"] += 1

            self.repository.link_movie_credit(movie_id, person_id, credit)
            summary["links_updated"] += 1
        return summary

    def selected_credits(self, credits: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[int, str]] = set()
        actors = sorted(
            credits.get("cast", []), key=lambda item: item.get("order", 9999)
        )
        for order, person in enumerate(actors[:10]):
            self._append(result, seen, person, "actor", order)

        roles = {
            "director": {"Director"},
            "producer": {"Producer"},
            "writer": self.WRITER_JOBS,
            "composer": self.COMPOSER_JOBS,
        }
        for role, jobs in roles.items():
            role_order = 0
            for person in credits.get("crew", []):
                if person.get("job") not in jobs:
                    continue
                if self._append(result, seen, person, role, role_order):
                    role_order += 1
        return result

    @staticmethod
    def _append(
        result: list[dict[str, Any]],
        seen: set[tuple[int, str]],
        person: dict[str, Any],
        role: str,
        order: int,
    ) -> bool:
        person_id = person.get("id")
        name = person.get("name") or person.get("original_name")
        if not person_id or not name or (person_id, role) in seen:
            return False
        seen.add((person_id, role))
        result.append(
            {
                "tmdb_person_id": person_id,
                "name": name,
                "credit_type": role,
                "sort_order": order,
                "credit_id": person.get("credit_id"),
                "character": person.get("character") if role == "actor" else None,
                "department": person.get("department"),
                "job": person.get("job"),
            }
        )
        return True

    @staticmethod
    def _empty_summary() -> dict[str, Any]:
        return {
            "movies_processed": 0,
            "people_created": 0,
            "people_refreshed": 0,
            "people_skipped": 0,
            "links_updated": 0,
            "failures": [],
        }

    @staticmethod
    def _merge(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key in (
            "movies_processed",
            "people_created",
            "people_refreshed",
            "people_skipped",
            "links_updated",
        ):
            target[key] += source[key]
        target["failures"].extend(source["failures"])
