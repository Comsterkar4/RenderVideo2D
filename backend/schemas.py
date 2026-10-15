from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class AspectRatio(StrEnum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class ImageProviderName(StrEnum):
    COMFYUI = "comfyui"
    GEMINI = "gemini"


class ImageGenerationOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ImageProviderName


class GeminiKeysUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    keys: list[SecretStr]


class GeminiKeysStatus(BaseModel):
    count: int
    source: Literal["web", "environment", "none"]
    volatile: bool


class VivibeKeyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: SecretStr


class VivibeKeyStatus(BaseModel):
    configured: bool
    source: Literal["web", "environment", "none"]
    volatile: bool


class VivibeVoiceRead(BaseModel):
    id: str
    name: str
    is_active: bool


class VivibeVoicesResponse(BaseModel):
    items: list[VivibeVoiceRead]
    default_voice_id: str | None


class AudioGenerationOptions(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    voice_id: str | None = Field(default=None, min_length=1, max_length=200)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    AWAITING_STORYBOARD_REVIEW = "awaiting_storyboard_review"
    GENERATING_ASSETS = "generating_assets"
    AWAITING_ASSET_REVIEW = "awaiting_asset_review"
    GENERATING_AUDIO = "generating_audio"
    RENDERING = "rendering"
    COMPLETED = "completed"


class ProjectCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    story: str = Field(min_length=1)
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    story: str | None = Field(default=None, min_length=1)
    aspect_ratio: AspectRatio | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "ProjectUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    name: str
    appearance: str
    prompt_fragment: str
    voice_id: str | None
    created_at: datetime
    updated_at: datetime


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    order: int = Field(validation_alias="order_index")
    duration_seconds: float
    character_ids: list[str]
    location: str
    narration: str
    image_prompt: str
    motion_prompt: str
    sound_effects: list[str]
    seed: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_id: str | None
    character_id: str | None
    kind: str
    local_path: str
    sha256: str | None
    provider: str
    model: str | None
    external_job_id: str | None
    status: str
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime
    updated_at: datetime


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    story: str
    language: str
    aspect_ratio: AspectRatio
    visual_style: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectRead):
    characters: list[CharacterRead]
    scenes: list[SceneRead]
    assets: list[AssetRead]
