from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Event, RLock, Thread
from typing import Callable
from uuid import uuid4

from app.core.cancellation import OperationCancelled
from app.schemas.recommendations import RecommendationResponse


class RecommendationJobNotFoundError(KeyError):
    pass


class RecommendationJobManager:
    TTL = timedelta(hours=24)

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = RLock()

    def start(
        self,
        runner: Callable[
            [Callable[[str], None], Callable[[], bool]],
            RecommendationResponse,
        ],
    ) -> dict:
        job_id = uuid4().hex
        with self._lock:
            self._discard_expired()
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "logs": [],
                "result": None,
                "error": None,
                "cancel_event": Event(),
                "created_at": datetime.now(timezone.utc),
            }
            self._append_log(self._jobs[job_id], "Задача подбора создана.")
        Thread(
            target=self._run,
            args=(job_id, runner),
            daemon=True,
            name=f"recommendation-{job_id[:8]}",
        ).start()
        return self.get(job_id)

    def get(self, job_id: str) -> dict:
        with self._lock:
            self._discard_expired()
            job = self._jobs.get(job_id)
            if job is None:
                raise RecommendationJobNotFoundError(job_id)
            return self._public(job)

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RecommendationJobNotFoundError(job_id)
            if job["status"] in {"pending", "running"}:
                job["cancel_event"].set()
                self._append_log(
                    job,
                    "Запрошена остановка. Ожидаем завершения текущего сетевого запроса.",
                )
            return self._public(job)

    def _run(self, job_id: str, runner: Callable) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
            self._append_log(job, "Подбор запущен.")

        def progress(message: str) -> None:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is not None:
                    self._append_log(current, message)

        def cancelled() -> bool:
            with self._lock:
                current = self._jobs.get(job_id)
                return current is None or current["cancel_event"].is_set()

        try:
            if cancelled():
                raise OperationCancelled()
            result = runner(progress, cancelled)
            if cancelled():
                raise OperationCancelled()
        except OperationCancelled:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "cancelled"
                self._append_log(job, "Подбор остановлен пользователем.")
        except Exception as error:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["error"] = str(error) or error.__class__.__name__
                self._append_log(job, f"Ошибка: {job['error']}")
        else:
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "completed"
                job["result"] = result
                self._append_log(job, "Подбор завершён.")

    @staticmethod
    def _append_log(job: dict, message: str) -> None:
        job["logs"].append(
            {
                "sequence": len(job["logs"]) + 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "message": message,
            }
        )

    @staticmethod
    def _public(job: dict) -> dict:
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "logs": list(job["logs"]),
            "result": job["result"],
            "error": job["error"],
        }

    def _discard_expired(self) -> None:
        cutoff = datetime.now(timezone.utc) - self.TTL
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job["created_at"] < cutoff
            and job["status"] in {"completed", "failed", "cancelled"}
        ]
        for job_id in expired:
            del self._jobs[job_id]
