from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.config import PROJECT_ROOT, VISUAL_STYLE
from backend.models import Character, Project, Scene
from backend.workflows.story_to_video.schemas import (
    CharacterPlan,
    ScenePlan,
    StoryboardPlan,
)


class StoryboardStateError(RuntimeError):
    pass


def load_project_with_storyboard(session: Session, project_id: str) -> Project | None:
    statement = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.characters),
            selectinload(Project.scenes).selectinload(Scene.characters),
            selectinload(Project.assets),
        )
    )
    return session.scalar(statement)


def replace_storyboard(
    session: Session,
    project: Project,
    storyboard: StoryboardPlan,
) -> Project:
    storyboard = storyboard.model_copy(update={"visual_style": VISUAL_STYLE})
    project.scenes.clear()
    project.characters.clear()
    session.flush()

    characters_by_key: dict[str, Character] = {}
    for character_plan in storyboard.characters:
        character = Character(
            key=character_plan.id,
            name=character_plan.name,
            appearance=character_plan.appearance,
            prompt_fragment=character_plan.prompt_fragment,
        )
        project.characters.append(character)
        characters_by_key[character.key] = character

    for scene_plan in sorted(storyboard.scenes, key=lambda scene: scene.order):
        scene = Scene(
            key=scene_plan.id,
            order_index=scene_plan.order,
            duration_seconds=scene_plan.duration_seconds,
            location=scene_plan.location,
            narration=scene_plan.narration,
            image_prompt=scene_plan.image_prompt,
            motion_prompt=scene_plan.motion_prompt,
            sound_effects=scene_plan.sound_effects,
            characters=[characters_by_key[key] for key in scene_plan.character_ids],
        )
        project.scenes.append(scene)

    project.title = storyboard.title
    project.visual_style = VISUAL_STYLE
    project.status = "awaiting_storyboard_review"
    session.commit()

    persisted = load_project_with_storyboard(session, project.id)
    if persisted is None:
        raise RuntimeError("Project disappeared after storyboard persistence")

    write_storyboard_artifacts(persisted, storyboard)
    return persisted


def storyboard_from_project(project: Project) -> StoryboardPlan:
    if not project.characters or not project.scenes:
        raise StoryboardStateError("Storyboard has not been generated")

    return StoryboardPlan(
        title=project.title,
        visual_style=VISUAL_STYLE,
        characters=[
            CharacterPlan(
                id=character.key,
                name=character.name,
                appearance=character.appearance,
                prompt_fragment=character.prompt_fragment,
            )
            for character in project.characters
        ],
        scenes=[
            ScenePlan(
                id=scene.key,
                order=scene.order_index,
                duration_seconds=scene.duration_seconds,
                character_ids=scene.character_ids,
                location=scene.location,
                narration=scene.narration,
                image_prompt=scene.image_prompt,
                motion_prompt=scene.motion_prompt,
                sound_effects=scene.sound_effects,
            )
            for scene in project.scenes
        ],
    )


def write_storyboard_artifacts(project: Project, storyboard: StoryboardPlan) -> None:
    project_directory = PROJECT_ROOT / "data" / "projects" / project.id
    project_directory.mkdir(parents=True, exist_ok=True)

    _replace_text_file(project_directory / "story.txt", project.story + "\n")
    _replace_text_file(
        project_directory / "storyboard.json",
        storyboard.model_dump_json(indent=2) + "\n",
    )


def _replace_text_file(destination: Path, content: str) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
