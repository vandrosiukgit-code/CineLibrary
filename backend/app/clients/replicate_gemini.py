from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ReplicateConfigurationError(RuntimeError):
    pass


class ReplicateAPIError(RuntimeError):
    pass


class ReplicateGeminiClient:
    def __init__(
        self,
        api_token: str,
        *,
        model: str = "google/gemini-3-flash",
        base_url: str = "https://api.replicate.com/v1",
        timeout: float = 180,
        thinking_level: str = "low",
    ) -> None:
        if not api_token.strip():
            raise ReplicateConfigurationError("REPLICATE_API_TOKEN is not configured")
        if thinking_level not in {"none", "low", "high"}:
            raise ReplicateConfigurationError(
                "GEMINI_THINKING_LEVEL must be none, low or high"
            )
        self.api_token = api_token
        self.model = model.strip("/")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.thinking_level = thinking_level

    @classmethod
    def from_environment(cls) -> "ReplicateGeminiClient":
        return cls(
            os.getenv("REPLICATE_API_TOKEN", ""),
            model=os.getenv("REPLICATE_MODEL", "google/gemini-3-flash"),
            base_url=os.getenv("REPLICATE_BASE_URL", "https://api.replicate.com/v1"),
            timeout=float(os.getenv("REPLICATE_TIMEOUT_SECONDS", "180")),
            thinking_level=os.getenv("GEMINI_THINKING_LEVEL", "low"),
        )

    def next_action(
        self,
        system_instruction: str,
        movie_input: str,
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = json.dumps(
            {"movieInput": movie_input, "toolHistory": history},
            ensure_ascii=False,
        )
        output = self._run(
            {
                "prompt": prompt,
                "system_instruction": system_instruction,
                "thinking_level": self.thinking_level,
                "temperature": 0,
                "top_p": 0.95,
                "max_output_tokens": 2048,
            }
        )
        return self._parse_action(output)

    def generate_json(
        self,
        system_instruction: str,
        payload: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
    ) -> Any:
        output = self.generate_text(
            system_instruction, payload,
            temperature=temperature, max_output_tokens=max_output_tokens,
        )
        return self._parse_json(output)

    def generate_text(
        self,
        system_instruction: str,
        payload: dict[str, Any],
        *,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        thinking_level: str | None = None,
    ) -> str:
        return self._run(
            {
                "prompt": json.dumps(payload, ensure_ascii=False),
                "system_instruction": system_instruction,
                "thinking_level": thinking_level if thinking_level is not None else self.thinking_level,
                "temperature": temperature,
                "top_p": 0.95,
                "max_output_tokens": max_output_tokens,
            }
        )

    def _run(self, model_input: dict[str, Any]) -> str:
        prediction = self._request(
            "POST",
            f"{self.base_url}/models/{self.model}/predictions",
            payload={"input": model_input},
            prefer_wait=True,
        )
        deadline = time.monotonic() + self.timeout
        while prediction.get("status") not in {"succeeded", "failed", "canceled"}:
            if time.monotonic() >= deadline:
                raise ReplicateAPIError("Replicate prediction timed out")
            get_url = (prediction.get("urls") or {}).get("get")
            if not get_url:
                raise ReplicateAPIError("Replicate returned no prediction status URL")
            time.sleep(0.5)
            prediction = self._request("GET", get_url)

        if prediction.get("status") != "succeeded":
            raise ReplicateAPIError("Replicate prediction failed")
        output = prediction.get("output")
        if isinstance(output, list):
            text = "".join(str(item) for item in output)
        elif isinstance(output, str):
            text = output
        else:
            raise ReplicateAPIError("Replicate returned an unexpected model output")
        if not text.strip():
            raise ReplicateAPIError("Replicate returned an empty model output")
        return text

    def _request(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        prefer_wait: bool = False,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }
        if prefer_wait:
            headers["Prefer"] = "wait"
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise ReplicateAPIError(
                f"Replicate API returned HTTP {error.code}"
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ReplicateAPIError("Replicate API request failed") from error

    @staticmethod
    def _parse_action(output: str) -> dict[str, Any]:
        action = ReplicateGeminiClient._parse_json(output)
        if not isinstance(action, dict):
            raise ReplicateAPIError("Gemini action must be a JSON object")
        return action

    @staticmethod
    def _parse_json(output: str) -> Any:
        text = output.strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise ReplicateAPIError("Gemini returned invalid JSON") from error
