from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any
from uuid import uuid4


class RecommendationSessionNotFoundError(KeyError):
    pass


class RecommendationSessionStore:
    """Process-local temporary catalog. Nothing here changes the movie database."""

    TTL = timedelta(hours=24)

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = RLock()

    def create(
        self,
        *,
        profile: dict[str, Any],
        prompt: str,
        recommendations: list[dict[str, Any]],
    ) -> str:
        with self._lock:
            self._discard_expired()
            session_id = uuid4().hex
            self._sessions[session_id] = {
                "created_at": datetime.now(timezone.utc),
                "profile": profile,
                "prompt": prompt,
                "recommendations": {
                    item["id"]: item for item in recommendations
                },
            }
            return session_id

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            self._discard_expired()
            session = self._sessions.get(session_id)
            if session is None:
                raise RecommendationSessionNotFoundError(session_id)
            return session

    def get_recommendation(
        self, session_id: str, recommendation_id: str
    ) -> dict[str, Any]:
        session = self.get(session_id)
        recommendation = session["recommendations"].get(recommendation_id)
        if recommendation is None:
            raise RecommendationSessionNotFoundError(recommendation_id)
        return recommendation

    def _discard_expired(self) -> None:
        cutoff = datetime.now(timezone.utc) - self.TTL
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if session["created_at"] < cutoff
        ]
        for session_id in expired:
            del self._sessions[session_id]
