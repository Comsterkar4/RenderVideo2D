from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, Scene
from backend.providers.speech.base import (
    SpeechProviderConfigurationError,
    SpeechProviderResponseError,
    SpeechProviderUnavailableError,
)
from backend.providers.speech.vivibe import VivibeSpeechProvider
from backend.schemas import AudioGenerationOptions, ProjectDetail
from backend.services.audio_service import (
    AUDIO_GENERATION_LOCK,
    AudioGenerationStateError,
    refresh_project_audio,
    regenerate_scene_audio,
    submit_missing_scene_audio,
)
from backend.services.storyboard_service import load_project_with_storyboard

router = APIRouter(tags=["audio"])
DatabaseSession = Annotated[Session, Depends(get_db)]


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




def audio_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AudioGenerationStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(
        exc,
        (SpeechProviderConfigurationError, SpeechProviderUnavailableError),
    ):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, SpeechProviderResponseError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    raise exc


def acquire_audio_lock() -> None:
    if not AUDIO_GENERATION_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another audio operation is already running",
        )




@router.post("/api/projects/{project_id}/audio/generate", response_model=ProjectDetail)
def generate_project_audio(
    project_id: str,
    options: AudioGenerationOptions,
    session: DatabaseSession,
) -> Project:
    acquire_audio_lock()
    try:
        project = require_project(session, project_id)
        provider = VivibeSpeechProvider()
        try:
            submit_missing_scene_audio(
                session,
                project,
                provider,
                options.speed,
            )
        except Exception as exc:
            raise audio_error(exc) from exc
        return require_project(session, project_id)
    finally:
        AUDIO_GENERATION_LOCK.release()


@router.post("/api/projects/{project_id}/audio/refresh", response_model=ProjectDetail)
def refresh_project_audio_status(
    project_id: str,
    session: DatabaseSession,
) -> Project:
    acquire_audio_lock()
    try:
        project = require_project(session, project_id)
        try:
            refresh_project_audio(session, project, VivibeSpeechProvider())
        except Exception as exc:
            raise audio_error(exc) from exc
        return require_project(session, project_id)
    finally:
        AUDIO_GENERATION_LOCK.release()


@router.post(
    "/api/projects/{project_id}/scenes/{scene_id}/audio",
    response_model=ProjectDetail,
)
def regenerate_project_scene_audio(
    project_id: str,
    scene_id: str,
    options: AudioGenerationOptions,
    session: DatabaseSession,
) -> Project:
    acquire_audio_lock()
    try:
        project = require_project(session, project_id)
        scene = require_scene(project, scene_id)
        try:
            regenerate_scene_audio(
                session,
                project,
                scene,
                VivibeSpeechProvider(),
                options.speed,
            )
        except Exception as exc:
            raise audio_error(exc) from exc
        return require_project(session, project_id)
    finally:
        AUDIO_GENERATION_LOCK.release()
