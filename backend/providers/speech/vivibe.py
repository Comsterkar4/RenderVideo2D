import os
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.providers.speech.base import (
    SpeechJobStatus,
    SpeechProviderConfigurationError,
    SpeechProviderResponseError,
    SpeechProviderUnavailableError,
    SpeechSubmission,
    SpeechVoice,
)


class VivibeKeyStore:
    def __init__(self) -> None:
        self._key: str | None = None
        self._lock = Lock()

    def replace(self, key: str) -> None:
        normalized = key.strip()
        if not normalized:
            raise ValueError("A ViViBe API key is required")
        with self._lock:
            self._key = normalized

    def clear(self) -> None:
        with self._lock:
            self._key = None

    def snapshot(self) -> str | None:
        with self._lock:
            return self._key


VIVIBE_KEY_STORE = VivibeKeyStore()


def configured_vivibe_api_key() -> str | None:
    web_key = VIVIBE_KEY_STORE.snapshot()
    if web_key:
        return web_key
    return os.getenv("VIVIBE_API_KEY", "").strip() or None


def vivibe_key_source() -> str:
    if VIVIBE_KEY_STORE.snapshot():
        return "web"
    return "environment" if os.getenv("VIVIBE_API_KEY", "").strip() else "none"


class VivibeSpeechProvider:
    name = "vivibe"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else configured_vivibe_api_key())
        self.base_url = (
            base_url
            or os.getenv("VIVIBE_API_URL", "https://api.lucylab.io/json-rpc")
        )
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("VIVIBE_TIMEOUT_SECONDS", "60")
        )
        self.max_download_bytes = int(
            os.getenv("VIVIBE_MAX_DOWNLOAD_BYTES", str(100 * 1024 * 1024))
        )
        self.transport = transport

    def list_voices(self) -> tuple[SpeechVoice, ...]:
        result = self._rpc(
            "getUserVoices",
            {
                "limit": 100,
                "page": 1,
            },
        )
        items = result.get("items")
        if not isinstance(items, list):
            raise SpeechProviderResponseError(
                "ViViBe getUserVoices response is missing result.items"
            )

        voices: list[SpeechVoice] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            voice_id = item.get("id")
            name = item.get("name")
            if isinstance(voice_id, str) and voice_id and isinstance(name, str) and name:
                voices.append(
                    SpeechVoice(
                        id=voice_id,
                        name=name,
                        is_active=item.get("isActive") is not False,
                    )
                )
        return tuple(voices)

    def submit(self, text: str, voice_id: str, speed: float) -> SpeechSubmission:
        result = self._rpc(
            "ttsLongText",
            {
                "text": text,
                "userVoiceId": voice_id,
                "speed": speed,
            },
        )
        job_id = result.get("projectExportId")
        if not isinstance(job_id, str) or not job_id:
            raise SpeechProviderResponseError(
                "ViViBe ttsLongText response is missing projectExportId"
            )
        return SpeechSubmission(
            job_id=job_id,
            character_count=self._optional_int(result.get("characterCount")),
            block_count=self._optional_int(result.get("blockCount")),
        )

    def status(self, job_id: str) -> SpeechJobStatus:
        result = self._rpc(
            "getExportStatus",
            {"projectExportId": job_id},
        )
        state = result.get("state")
        if state not in {"pending", "processing", "completed", "failed"}:
            raise SpeechProviderResponseError(
                f"ViViBe returned an unknown export state: {state or 'missing'}"
            )
        audio_url = result.get("url")
        subtitle_url = result.get("srtUrl")
        if state == "completed" and (not isinstance(audio_url, str) or not audio_url):
            raise SpeechProviderResponseError(
                "ViViBe completed the export without an audio URL"
            )
        error = result.get("error") or result.get("message")
        return SpeechJobStatus(
            state=state,
            audio_url=audio_url if isinstance(audio_url, str) else None,
            subtitle_url=subtitle_url if isinstance(subtitle_url, str) else None,
            error=error if isinstance(error, str) else None,
        )

    def download(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SpeechProviderResponseError("ViViBe returned an invalid download URL")

        try:
            with httpx.Client(
                timeout=httpx.Timeout(
                    connect=10,
                    read=self.timeout_seconds,
                    write=30,
                    pool=10,
                ),
                follow_redirects=True,
                transport=self.transport,
            ) as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > self.max_download_bytes:
                            raise SpeechProviderResponseError(
                                "ViViBe download exceeds the configured size limit"
                            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429 or exc.response.status_code >= 500:
                raise SpeechProviderUnavailableError(
                    f"ViViBe download is temporarily unavailable (HTTP {exc.response.status_code})"
                ) from exc
            raise SpeechProviderResponseError(
                f"ViViBe download returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise SpeechProviderUnavailableError(
                "ViViBe download failed to connect"
            ) from exc

        if not content:
            raise SpeechProviderResponseError("ViViBe returned an empty download")
        return bytes(content)

    def _rpc(self, method: str, input_data: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise SpeechProviderConfigurationError(
                "No ViViBe API key is configured on the backend"
            )

        try:
            with httpx.Client(
                timeout=httpx.Timeout(
                    connect=10,
                    read=self.timeout_seconds,
                    write=30,
                    pool=10,
                ),
                transport=self.transport,
            ) as client:
                response = client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "method": method,
                        "input": input_data,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._error_detail(exc.response).replace(
                self.api_key,
                "[redacted]",
            )
            if exc.response.status_code == 429 or exc.response.status_code >= 500:
                raise SpeechProviderUnavailableError(
                    f"ViViBe is temporarily unavailable (HTTP {exc.response.status_code})"
                ) from exc
            raise SpeechProviderResponseError(
                f"ViViBe returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise SpeechProviderUnavailableError(
                "ViViBe request failed to connect"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise SpeechProviderResponseError("ViViBe returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise SpeechProviderResponseError("ViViBe returned an invalid response")
        if body.get("error"):
            detail = self._error_detail(response).replace(self.api_key, "[redacted]")
            raise SpeechProviderResponseError(f"ViViBe API error: {detail}")
        result = body.get("result")
        if not isinstance(result, dict):
            raise SpeechProviderResponseError("ViViBe response is missing result")
        return result

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    message = error.get("message")
                    if isinstance(message, str) and message:
                        return message[:500]
                if isinstance(error, str) and error:
                    return error[:500]
                message = payload.get("message")
                if isinstance(message, str) and message:
                    return message[:500]
        except (TypeError, ValueError):
            pass
        return response.text[:500] or "request failed"
