from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectDetail, RenderGenerationOptions
from backend.services.storyboard_service import load_project_with_storyboard
from backend.services.video_service import (
    RENDER_LOCK,
    VideoRenderError,
    render_project,
)


router = APIRouter(tags=["render"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def require_project(session: Session, project_id: str) -> Project:
    project = load_project_with_storyboard(session, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


def acquire_render_lock() -> None:
    if not RENDER_LOCK.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another video render is already running",
        )


def render_error(exc: Exception) -> HTTPException:
    if isinstance(exc, VideoRenderError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Video rendering failed",
    )


@router.post(
    "/api/projects/{project_id}/render",
    response_model=ProjectDetail,
)
def render_project_video(
    project_id: str,
    options: RenderGenerationOptions,
    session: DatabaseSession,
) -> Project:
    acquire_render_lock()
    try:
        project = require_project(session, project_id)
        try:
            render_project(session, project, options.quality)
        except Exception as exc:
            raise render_error(exc) from exc
        return require_project(session, project_id)
    finally:
        RENDER_LOCK.release()
