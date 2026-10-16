import hashlib
import json
import os
import secrets
from pathlib import Path
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.models import Asset, Project, Scene
from backend.providers.image.base import ImageGenerationRequest, ImageProvider

IMAGE_GENERATION_LOCK = Lock()
DEFAULT_NEGATIVE_PROMPT = (
    "photorealistic, realistic photo, photograph, live action, 3d, cgi, "
    "rendered 3d, realistic skin texture, glossy plastic, camera, lens, "
    "depth of field, text, watermark, logo, signature, collage, split screen, "
    "multiple panels, blurry, low quality, deformed hands, extra fingers, "
    "extra limbs, duplicate person, cropped face"
)
TWO_D_CARTOON_PROMPT_PREFIX = (
    "2D cartoon illustration for a children's picture book, hand-drawn "
    "storybook art, bold clean ink outlines, flat cel shading, simple rounded "
    "shapes, warm vibrant colors, clearly illustrated not photographic"
)


class ImageGenerationStateError(RuntimeError):
    pass


def generate_missing_scene_images(
    session: Session,
    project: Project,
    provider: ImageProvider,
) -> None:
    require_image_generation_state(project)
    for scene in project.scenes:
        if current_scene_image(session, project.id, scene.id) is None:
            generate_scene_image(session, project, scene, provider, regenerate=False)

    update_project_image_status(session, project)


def regenerate_scene_image(
    session: Session,
    project: Project,
    scene: Scene,
    provider: ImageProvider,
) -> Asset:
    require_image_generation_state(project)
    asset = generate_scene_image(session, project, scene, provider, regenerate=True)
    update_project_image_status(session, project)
    return asset


def generate_scene_image(
    session: Session,
    project: Project,
    scene: Scene,
    provider: ImageProvider,
    *,
    regenerate: bool,
) -> Asset:
    existing = current_scene_image(session, project.id, scene.id)
    if existing is not None and not regenerate:
        return existing

    seed = secrets.randbits(63) if regenerate else stable_scene_seed(project.id, scene.key)
    positive_prompt = build_positive_prompt(scene)
    negative_prompt = os.getenv("COMFYUI_NEGATIVE_PROMPT", DEFAULT_NEGATIVE_PROMPT)
    generated_request = ImageGenerationRequest(
        prompt=positive_prompt,
        negative_prompt=negative_prompt,
        aspect_ratio=project.aspect_ratio,
        seed=seed,
        filename_prefix=f"render-video/{project.id}/{scene.key}",
    )

    asset = Asset(
        project=project,
        scene=scene,
        kind="scene_image",
        local_path="",
        provider=provider.name,
        model=provider.model,
        status="processing",
        metadata_json={},
    )
    session.add(asset)
    session.flush()

    scene.seed = seed
    scene.status = "generating"
    project.status = "generating_assets"
    session.commit()

    try:
        generated = provider.generate(generated_request)
        image_sha256 = hashlib.sha256(generated.content).hexdigest()
        metadata = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "mime_type": generated.media_type,
            **generated.metadata,
        }
        relative_image_path = (
            Path("data")
            / "projects"
            / project.id
            / "scenes"
            / scene.key
            / f"{asset.id}{generated.file_extension}"
        )
        asset.local_path = relative_image_path.as_posix()
        image_path = PROJECT_ROOT / relative_image_path
        write_bytes_atomically(image_path, generated.content)
        write_text_atomically(
            image_path.with_suffix(".metadata.json"),
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        )

        asset.sha256 = image_sha256
        asset.external_job_id = generated.external_job_id
        asset.status = "completed"
        asset.metadata_json = metadata
        scene.status = "image_ready"
        session.commit()
        return asset
    except Exception as exc:
        session.rollback()
        failed_asset = session.get(Asset, asset.id)
        failed_scene = session.get(Scene, scene.id)
        failed_project = session.get(Project, project.id)
        if failed_asset is not None:
            failed_asset.status = "failed"
            failed_asset.metadata_json = {"error": str(exc)}
        if failed_scene is not None:
            failed_scene.status = "image_failed"
        if failed_project is not None:
            failed_project.status = "generating_assets"
        session.commit()
        raise


def current_scene_image(session: Session, project_id: str, scene_id: str) -> Asset | None:
    statement = (
        select(Asset)
        .where(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.kind == "scene_image",
            Asset.status == "completed",
        )
        .order_by(Asset.created_at.desc())
    )
    for asset in session.scalars(statement):
        if (PROJECT_ROOT / asset.local_path).is_file():
            return asset
    return None


def update_project_image_status(session: Session, project: Project) -> None:
    ready = all(
        current_scene_image(session, project.id, scene.id) is not None
        for scene in project.scenes
    )
    project.status = "awaiting_asset_review" if ready else "generating_assets"
    session.commit()


def require_image_generation_state(project: Project) -> None:
    if project.status not in {"generating_assets", "awaiting_asset_review"}:
        raise ImageGenerationStateError(
            "Storyboard must be approved before generating scene images"
        )
    if not project.scenes:
        raise ImageGenerationStateError("Project has no scenes")


def build_positive_prompt(scene: Scene) -> str:
    parts = [
        TWO_D_CARTOON_PROMPT_PREFIX,
        scene.image_prompt,
        "single coherent scene, one animation frame, clear focal subject, no text",
    ]
    return ". ".join(part.strip().rstrip(".") for part in parts if part.strip()) + "."


def stable_scene_seed(project_id: str, scene_key: str) -> int:
    digest = hashlib.sha256(f"{project_id}:{scene_key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def write_bytes_atomically(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(destination)


def write_text_atomically(destination: Path, content: str) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
