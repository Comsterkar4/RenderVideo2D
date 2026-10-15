import os

import httpx
from pydantic import ValidationError

from backend.models import Project
from backend.workflows.story_to_video.prompts import SYSTEM_PROMPT, build_storyboard_prompt
from backend.workflows.story_to_video.schemas import StoryboardPlan


class OllamaProviderError(RuntimeError):
    pass


class OllamaUnavailableError(OllamaProviderError):
    pass


class OllamaResponseError(OllamaProviderError):
    pass


class OllamaStoryProvider:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_STORY_MODEL", "qwen2.5:3b")

    def analyze(self, project: Project) -> StoryboardPlan:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_storyboard_prompt(project)},
            ],
            "stream": False,
            "format": StoryboardPlan.model_json_schema(),
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
            },
        }

        timeout = httpx.Timeout(connect=10, read=600, write=30, pool=10)
        try:
            with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                response = client.post("/api/chat", json=payload)
                response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise OllamaUnavailableError(
                f"Cannot connect to Ollama at {self.base_url}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError("Ollama analysis timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise OllamaResponseError(
                f"Ollama returned HTTP {exc.response.status_code}: {detail}"
            ) from exc

        try:
            content = response.json()["message"]["content"]
            return StoryboardPlan.model_validate_json(content)
        except (KeyError, TypeError, ValueError, ValidationError) as exc:
            raise OllamaResponseError("Ollama returned an invalid storyboard") from exc

    def unload(self) -> None:
        payload = {
            "model": self.model,
            "keep_alive": 0,
        }
        timeout = httpx.Timeout(connect=5, read=30, write=10, pool=5)
        try:
            with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                response = client.post("/api/generate", json=payload)
                response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return
        except httpx.HTTPError as exc:
            raise OllamaResponseError("Ollama could not release model memory") from exc


def get_ollama_story_provider() -> OllamaStoryProvider:
    return OllamaStoryProvider()
