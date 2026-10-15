from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.providers.llm.ollama import (
    OllamaResponseError,
    OllamaStoryProvider,
    OllamaUnavailableError,
    get_ollama_story_provider,
)
from backend.schemas import ProjectDetail
from backend.services.storyboard_service import (
    StoryboardStateError,
    load_project_with_storyboard,
    replace_storyboard,
    storyboard_from_project,
)
from backend.workflows.story_to_video.schemas import StoryboardPlan

router = APIRouter(prefix="/api/projects", tags=["storyboard"])
DatabaseSession = Annotated[Session, Depends(get_db)]
StoryProvider = Annotated[OllamaStoryProvider, Depends(get_ollama_story_provider)]

EDITABLE_STORYBOARD_STATES = {"draft", "awaiting_storyboard_review"}


def require_project(session: Session, project_id: str) -> Project:
    project = load_project_with_storyboard(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def require_editable_storyboard(project: Project) -> None:
    if project.status not in EDITABLE_STORYBOARD_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Storyboard cannot be changed while project status is {project.status}",
        )


@router.post("/{project_id}/analyze", response_model=ProjectDetail)
def analyze_project(
    project_id: str,
    session: DatabaseSession,
    provider: StoryProvider,
) -> Project:
    project = require_project(session, project_id)
    require_editable_storyboard(project)

    previous_status = project.status
    project.status = "analyzing"
    session.commit()

    try:
        storyboard = provider.analyze(project)
    except OllamaUnavailableError as exc:
        project.status = previous_status
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OllamaResponseError as exc:
        project.status = previous_status
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return replace_storyboard(session, project, storyboard)


@router.get("/{project_id}/storyboard", response_model=StoryboardPlan)
def get_storyboard(project_id: str, session: DatabaseSession) -> StoryboardPlan:
    project = require_project(session, project_id)
    try:
        return storyboard_from_project(project)
    except StoryboardStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.put("/{project_id}/storyboard", response_model=ProjectDetail)
def replace_project_storyboard(
    project_id: str,
    payload: StoryboardPlan,
    session: DatabaseSession,
) -> Project:
    project = require_project(session, project_id)
    require_editable_storyboard(project)
    return replace_storyboard(session, project, payload)


@router.post("/{project_id}/storyboard/approve", response_model=ProjectDetail)
def approve_storyboard(project_id: str, session: DatabaseSession) -> Project:
    project = require_project(session, project_id)
    if project.status != "awaiting_storyboard_review":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a storyboard awaiting review can be approved",
        )

    project.status = "generating_assets"
    session.commit()
    return require_project(session, project_id)
