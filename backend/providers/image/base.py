from dataclasses import dataclass, field
from typing import Any, Protocol


class ImageProviderError(RuntimeError):
    pass


class ImageProviderConfigurationError(ImageProviderError):
    pass


class ImageProviderUnavailableError(ImageProviderError):
    pass


class ImageProviderResponseError(ImageProviderError):
    pass


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    negative_prompt: str
    aspect_ratio: str
    seed: int
    filename_prefix: str


@dataclass(frozen=True)
class GeneratedImage:
    content: bytes
    media_type: str
    file_extension: str
    external_job_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class ImageProvider(Protocol):
    name: str
    model: str
    uses_local_gpu: bool

    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        ...

    def release(self) -> None:
        ...
