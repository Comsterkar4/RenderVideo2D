from dataclasses import dataclass
from typing import Protocol


class SpeechProviderError(RuntimeError):
    pass


class SpeechProviderConfigurationError(SpeechProviderError):
    pass


class SpeechProviderUnavailableError(SpeechProviderError):
    pass


class SpeechProviderResponseError(SpeechProviderError):
    pass


@dataclass(frozen=True)
class SpeechVoice:
    id: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class SpeechSubmission:
    job_id: str
    character_count: int | None
    block_count: int | None


@dataclass(frozen=True)
class SpeechJobStatus:
    state: str
    audio_url: str | None = None
    subtitle_url: str | None = None
    error: str | None = None


class SpeechProvider(Protocol):
    name: str

    def list_voices(self) -> tuple[SpeechVoice, ...]: ...

    def submit(self, text: str, voice_id: str, speed: float) -> SpeechSubmission: ...

    def status(self, job_id: str) -> SpeechJobStatus: ...

    def download(self, url: str) -> bytes: ...
