import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.database import get_db
from backend.models import Asset, Project, Scene
from backend.providers.image.base import (
    ImageProvider,
    ImageProviderConfigurationError,
    ImageProviderError,
    ImageProviderResponseError,
    ImageProviderUnavailableError,
)
from backend.providers.image.comfyui import ComfyUIImageProvider
from backend.providers.image.gemini import (
    GEMINI_KEY_STORE,
    GeminiImageProvider,
    configured_gemini_api_keys,
    gemini_key_source,
)
from backend.providers.llm.ollama import OllamaProviderError, OllamaStoryProvider
from backend.schemas import (
    GeminiKeysStatus,
    GeminiKeysUpdate,
    ImageGenerationOptions,
    ImageProviderName,
    ProjectDetail,
)
from backend.services.image_service import (
    IMAGE_GENERATION_LOCK,
    ImageGenerationStateError,
    current_scene_image,
    generate_missing_scene_images,
    regenerate_scene_image,
)
from backend.services.storyboard_service import load_project_with_storyboard

router = APIRouter(tags=["images"])
DatabaseSession = Annotated[Session, Depends(get_db)]
LOGGER = logging.getLogger(__name__)


def create_image_provider(provider_name: ImageProviderName) -> ImageProvider:
    if provider_name is ImageProviderName.GEMINI:
        return GeminiImageProvider()
    return ComfyUIImageProvider()


def require_project(session: Session, project_id: str) -> Project:
    project = load_project_with_storyboard(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def require_scene(project: Project, scene_id: str) -> Scene:
    scene = next((candidate for candidate in project.scenes if candidate.id == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


def release_story_model() -> None:
    try:
        OllamaStoryProvider().unload()
    except OllamaProviderError as exc:
        LOGGER.warning("Could not release Ollama model memory: %s", exc)


def release_image_model(provider: ImageProvider) -> None:
    try:
        provider.release()
    except ImageProviderError as exc:
        LOGGER.warning("Could not release %s image provider: %s", provider.name, exc)


def image_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ImageGenerationStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(
        exc,
        (ImageProviderConfigurationError, ImageProviderUnavailableError),
    ):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, ImageProviderResponseError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    raise exc


def current_gemini_key_status() -> GeminiKeysStatus:
    source = gemini_key_source()
    return GeminiKeysStatus(
        count=len(configured_gemini_api_keys()),
        source=source,
        volatile=source == "web",
    )


@router.get("/api/settings/gemini-keys", response_model=GeminiKeysStatus)
def get_gemini_keys() -> GeminiKeysStatus:
    return current_gemini_key_status()


@router.put("/api/settings/gemini-keys", response_model=GeminiKeysStatus)
def replace_gemini_keys(settings: GeminiKeysUpdate) -> GeminiKeysStatus:
    try:
        GEMINI_KEY_STORE.replace(
            [key.get_secret_value() for key in settings.keys]
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return current_gemini_key_status()


@router.delete("/api/settings/gemini-keys", response_model=GeminiKeysStatus)
def clear_gemini_keys() -> GeminiKeysStatus:
    GEMINI_KEY_STORE.clear()
    return current_gemini_key_status()


@router.post("/api/projects/{project_id}/images/generate", response_model=ProjectDetail)
def generate_project_images(
    project_id: str,
    options: ImageGenerationOptions,
    session: DatabaseSession,
) -> Project:
    provider = create_image_provider(options.provider)
    if not IMAGE_GENERATION_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another image generation job is already running",
        )

    try:
        project = require_project(session, project_id)
        if provider.uses_local_gpu:
            release_story_model()
        try:
            generate_missing_scene_images(session, project, provider)
        except Exception as exc:
            raise image_error(exc) from exc
        finally:
            release_image_model(provider)
        return require_project(session, project_id)
    finally:
        IMAGE_GENERATION_LOCK.release()


@router.post(
    "/api/projects/{project_id}/scenes/{scene_id}/image",
    response_model=ProjectDetail,
)
def retry_scene_image(
    project_id: str,
    scene_id: str,
    options: ImageGenerationOptions,
    session: DatabaseSession,
) -> Project:
    provider = create_image_provider(options.provider)
    if not IMAGE_GENERATION_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another image generation job is already running",
        )

    try:
        project = require_project(session, project_id)
        scene = require_scene(project, scene_id)
        if provider.uses_local_gpu:
            release_story_model()
        try:
            regenerate_scene_image(session, project, scene, provider)
        except Exception as exc:
            raise image_error(exc) from exc
        finally:
            release_image_model(provider)
        return require_project(session, project_id)
    finally:
        IMAGE_GENERATION_LOCK.release()


@router.post("/api/projects/{project_id}/images/approve", response_model=ProjectDetail)
def approve_project_images(project_id: str, session: DatabaseSession) -> Project:
    project = require_project(session, project_id)
    if project.status != "awaiting_asset_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="All scene images must be ready before approval",
        )

    missing = [
        scene.key
        for scene in project.scenes
        if current_scene_image(session, project.id, scene.id) is None
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Missing scene images: {', '.join(missing)}",
        )

    project.status = "generating_audio"
    session.commit()
    return require_project(session, project_id)


@router.get("/api/assets/{asset_id}/content", response_class=FileResponse)
def get_asset_content(asset_id: str, session: DatabaseSession) -> FileResponse:
    asset = session.get(Asset, asset_id)
    if asset is None or asset.status != "completed":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    project_root = (PROJECT_ROOT / "data" / "projects").resolve()
    asset_path = (PROJECT_ROOT / asset.local_path).resolve()
    if not asset_path.is_relative_to(project_root) or not asset_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset file not found")

    media_type = asset.metadata_json.get("mime_type")
    allowed_media_types = {
        "image/png",
        "image/jpeg",
        "audio/wav",
        "application/x-subrip",
        "video/mp4",
    }
    if media_type not in allowed_media_types:
        media_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".wav": "audio/wav",
            ".srt": "application/x-subrip",
        }.get(asset_path.suffix.lower(), "application/octet-stream")
    return FileResponse(asset_path, media_type=media_type)
