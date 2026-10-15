import base64
import binascii
import os
from threading import Lock
from typing import Any, Iterator, Sequence

import httpx

from backend.providers.image.base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageProviderConfigurationError,
    ImageProviderResponseError,
    ImageProviderUnavailableError,
)


MAX_GEMINI_KEYS = 20


class GeminiKeyStore:
    def __init__(self) -> None:
        self._keys: tuple[str, ...] = ()
        self._lock = Lock()

    def replace(self, keys: Sequence[str]) -> None:
        normalized = tuple(dict.fromkeys(key.strip() for key in keys if key.strip()))
        if not normalized:
            raise ValueError("At least one Gemini API key is required")
        if len(normalized) > MAX_GEMINI_KEYS:
            raise ValueError(f"At most {MAX_GEMINI_KEYS} Gemini API keys are allowed")
        with self._lock:
            self._keys = normalized

    def clear(self) -> None:
        with self._lock:
            self._keys = ()

    def snapshot(self) -> tuple[str, ...]:
        with self._lock:
            return self._keys

    def promote(self, key: str) -> None:
        with self._lock:
            if key not in self._keys or self._keys[0] == key:
                return
            self._keys = (key, *(candidate for candidate in self._keys if candidate != key))


GEMINI_KEY_STORE = GeminiKeyStore()


def configured_gemini_api_keys() -> tuple[str, ...]:
    web_keys = GEMINI_KEY_STORE.snapshot()
    if web_keys:
        return web_keys
    environment_key = os.getenv("GEMINI_API_KEY", "").strip()
    return (environment_key,) if environment_key else ()


def gemini_key_source() -> str:
    if GEMINI_KEY_STORE.snapshot():
        return "web"
    return "environment" if os.getenv("GEMINI_API_KEY", "").strip() else "none"


class GeminiImageProvider:
    name = "gemini"
    uses_local_gpu = False

    def __init__(
        self,
        api_keys: Sequence[str] | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_keys = (
            tuple(key.strip() for key in api_keys if key.strip())
            if api_keys is not None
            else configured_gemini_api_keys()
        )
        self.base_url = (
            base_url
            or os.getenv(
                "GEMINI_API_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            )
        ).rstrip("/")
        self.model = model or os.getenv("GEMINI_IMAGE_MODEL", "gemini-nano-banana-2.1")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("GEMINI_IMAGE_TIMEOUT_SECONDS", "300")
        )
        self.transport = transport

    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        if not self.api_keys:
            raise ImageProviderConfigurationError(
                "No Gemini API key is configured on the backend"
            )

        prompt = (
            f"{request.prompt}\n\n"
            f"Do not include any of the following: {request.negative_prompt}."
        )
        payload = {
            "model": self.model,
            "input": [{"type": "text", "text": prompt}],
            "response_format": {
                "type": "image",
                "mime_type": "image/jpeg",
                "aspect_ratio": request.aspect_ratio,
            },
        }
        timeout = httpx.Timeout(
            connect=10,
            read=self.timeout_seconds,
            write=30,
            pool=10,
        )
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=timeout,
                transport=self.transport,
            ) as client:
                response = None
                for index, api_key in enumerate(self.api_keys):
                    try:
                        response = client.post(
                            "/interactions",
                            headers={"x-goog-api-key": api_key},
                            json=payload,
                        )
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        detail = self._error_detail(exc.response).replace(
                            api_key,
                            "[redacted]",
                        )
                        if index + 1 < len(self.api_keys) and self._should_try_next_key(
                            exc.response,
                            detail,
                        ):
                            continue
                        raise ImageProviderResponseError(
                            f"Gemini returned HTTP {exc.response.status_code}: {detail}"
                        ) from exc
                    GEMINI_KEY_STORE.promote(api_key)
                    break
        except httpx.RequestError as exc:
            raise ImageProviderUnavailableError(
                "Gemini image request failed to connect"
            ) from exc

        if response is None:
            raise ImageProviderResponseError("Gemini did not return a response")

        try:
            body = response.json()
        except ValueError as exc:
            raise ImageProviderResponseError("Gemini returned invalid JSON") from exc

        image = self._find_image(body)
        mime_type = image.get("mime_type")
        if mime_type != "image/jpeg":
            raise ImageProviderResponseError(
                f"Gemini returned unsupported image type: {mime_type or 'unknown'}"
            )
        try:
            content = base64.b64decode(image["data"], validate=True)
        except (KeyError, TypeError, ValueError, binascii.Error) as exc:
            raise ImageProviderResponseError("Gemini returned invalid image data") from exc
        if not content:
            raise ImageProviderResponseError("Gemini returned an empty image")

        interaction_id = body.get("id")
        return GeneratedImage(
            content=content,
            media_type=mime_type,
            file_extension=".jpg",
            external_job_id=str(interaction_id) if interaction_id else None,
            metadata={
                "aspect_ratio": request.aspect_ratio,
                "interaction_id": interaction_id,
            },
        )

    def release(self) -> None:
        return None

    @staticmethod
    def _find_image(body: Any) -> dict[str, Any]:
        if not isinstance(body, dict):
            raise ImageProviderResponseError("Gemini returned an invalid response")
        for step in GeminiImageProvider._dict_nodes(body.get("steps", [])):
            if step.get("type") != "model_output":
                continue
            for content in GeminiImageProvider._dict_nodes(step.get("content", [])):
                if content.get("type") == "image" and content.get("data"):
                    return content
        raise ImageProviderResponseError("Gemini completed without an image output")

    @staticmethod
    def _dict_nodes(value: Any) -> Iterator[dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from GeminiImageProvider._dict_nodes(child)
        elif isinstance(value, list):
            for child in value:
                yield from GeminiImageProvider._dict_nodes(child)

    @staticmethod
    def _should_try_next_key(response: httpx.Response, detail: str) -> bool:
        if response.status_code in {401, 403, 429} or response.status_code >= 500:
            return True
        normalized = detail.casefold()
        return response.status_code == 400 and (
            "api key not valid" in normalized or "api_key_invalid" in normalized
        )


    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            for error in GeminiImageProvider._dict_nodes(payload):
                message = error.get("message")
                if isinstance(message, str) and message:
                    return message[:500]
        except (TypeError, ValueError):
            pass
        return response.text[:500] or "request failed"
