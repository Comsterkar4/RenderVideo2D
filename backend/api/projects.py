import shutil

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.config import PROJECT_ROOT, VIDEO_LANGUAGE, VISUAL_STYLE
from backend.database import get_db
from backend.models import Project, Scene
from backend.schemas import ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def project_detail_query(project_id: str):
    return (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.characters),
            selectinload(Project.scenes).selectinload(Scene.characters),
            selectinload(Project.assets),
        )
    )


def find_project_or_404(session: Session, project_id: str) -> Project:
    project = session.scalar(project_detail_query(project_id))
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: DatabaseSession) -> Project:
    project = Project(
        **payload.model_dump(mode="json"),
        language=VIDEO_LANGUAGE,
        visual_style=VISUAL_STYLE,
    )
    session.add(project)
    session.commit()
    return find_project_or_404(session, project.id)


@router.get("", response_model=list[ProjectRead])
def list_projects(session: DatabaseSession) -> list[Project]:
    statement = select(Project).order_by(Project.created_at.desc())
    return list(session.scalars(statement))


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, session: DatabaseSession) -> Project:
    return find_project_or_404(session, project_id)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    session: DatabaseSession,
) -> Project:
    project = find_project_or_404(session, project_id)
    for field_name, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(project, field_name, value)

    session.commit()
    return find_project_or_404(session, project_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, session: DatabaseSession) -> Response:
    project = find_project_or_404(session, project_id)
    project_directory = PROJECT_ROOT / "data" / "projects" / project.id
    if project_directory.is_dir():
        shutil.rmtree(project_directory)

    session.delete(project)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
