import hashlib
import io
import json
import wave
from pathlib import Path
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.models import Asset, Project, Scene
from backend.providers.speech.base import (
    SpeechJobStatus,
    SpeechProvider,
    SpeechProviderResponseError,
    SpeechProviderUnavailableError,
)

AUDIO_GENERATION_LOCK = Lock()
ACTIVE_AUDIO_STATUSES = {"submitting", "processing"}


class AudioGenerationStateError(RuntimeError):
    pass


def submit_missing_scene_audio(
    session: Session,
    project: Project,
    provider: SpeechProvider,
    voice_id: str,
    speed: float,
) -> None:
    require_audio_generation_state(project)
    for scene in project.scenes:
        submit_scene_audio(
            session,
            project,
            scene,
            provider,
            voice_id,
            speed,
            regenerate=False,
        )


def regenerate_scene_audio(
    session: Session,
    project: Project,
    scene: Scene,
    provider: SpeechProvider,
    voice_id: str,
    speed: float,
) -> Asset:
    require_audio_generation_state(project)
    return submit_scene_audio(
        session,
        project,
        scene,
        provider,
        voice_id,
        speed,
        regenerate=True,
    )


def submit_scene_audio(
    session: Session,
    project: Project,
    scene: Scene,
    provider: SpeechProvider,
    voice_id: str,
    speed: float,
    *,
    regenerate: bool,
) -> Asset:
    narration_sha256 = hashlib.sha256(scene.narration.encode("utf-8")).hexdigest()
    requested_metadata = {
        "narration_sha256": narration_sha256,
        "voice_id": voice_id,
        "speed": speed,
    }
    active = active_scene_audio(session, project.id, scene.id)
    if active is not None:
        if audio_matches(active, requested_metadata):
            return active
        raise AudioGenerationStateError(
            f"Scene {scene.key} already has an audio job in progress"
        )

    existing = current_scene_audio(session, project.id, scene.id)
    if existing is not None and audio_matches(existing, requested_metadata) and not regenerate:
        return existing
    if existing is not None:
        supersede_completed_assets(session, project.id, scene.id, "narration_audio")
        supersede_completed_assets(session, project.id, scene.id, "narration_subtitle")

    asset = Asset(
        project=project,
        scene=scene,
        kind="narration_audio",
        local_path="",
        provider=provider.name,
        status="submitting",
        metadata_json=requested_metadata,
    )
    session.add(asset)
    scene.status = "audio_submitting"
    project.status = "generating_audio"
    session.commit()

    try:
        submission = provider.submit(scene.narration, voice_id, speed)
        asset.external_job_id = submission.job_id
        asset.status = "processing"
        asset.metadata_json = {
            **requested_metadata,
            "character_count": submission.character_count,
            "block_count": submission.block_count,
            "provider_state": "pending",
        }
        scene.status = "audio_processing"
        session.commit()
        return asset
    except Exception as exc:
        session.rollback()
        failed_asset = session.get(Asset, asset.id)
        failed_scene = session.get(Scene, scene.id)
        if failed_asset is not None:
            failed_asset.status = "failed"
            failed_asset.metadata_json = {
                **requested_metadata,
                "error": str(exc),
            }
        if failed_scene is not None:
            failed_scene.status = "audio_failed"
        session.commit()
        raise


def refresh_project_audio(
    session: Session,
    project: Project,
    provider: SpeechProvider,
) -> None:
    require_audio_generation_state(project)
    processing_assets = list(
        session.scalars(
            select(Asset)
            .where(
                Asset.project_id == project.id,
                Asset.kind == "narration_audio",
                Asset.status.in_(ACTIVE_AUDIO_STATUSES),
            )
            .order_by(Asset.created_at)
        )
    )

    scenes_by_id = {scene.id: scene for scene in project.scenes}
    for asset in processing_assets:
        scene = scenes_by_id.get(asset.scene_id or "")
        if scene is None or not asset.external_job_id:
            mark_audio_failed(session, asset, scene, "Audio job metadata is incomplete")
            continue

        try:
            job_status = provider.status(asset.external_job_id)
            if job_status.state in {"pending", "processing"}:
                asset.metadata_json = {
                    **asset.metadata_json,
                    "provider_state": job_status.state,
                }
                continue
            if job_status.state == "failed":
                mark_audio_failed(
                    session,
                    asset,
                    scene,
                    job_status.error or "ViViBe audio generation failed",
                )
                continue
            complete_audio_asset(session, project, scene, asset, provider, job_status)
        except SpeechProviderUnavailableError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            failed_asset = session.get(Asset, asset.id)
            failed_scene = session.get(Scene, scene.id)
            if failed_asset is not None:
                mark_audio_failed(session, failed_asset, failed_scene, str(exc))

    session.commit()
    project.status = (
        "rendering"
        if project.scenes
        and all(
            current_scene_audio(session, project.id, scene.id) is not None
            for scene in project.scenes
        )
        else "generating_audio"
    )
    session.commit()


def complete_audio_asset(
    session: Session,
    project: Project,
    scene: Scene,
    asset: Asset,
    provider: SpeechProvider,
    job_status: SpeechJobStatus,
) -> None:
    if not job_status.audio_url:
        raise SpeechProviderResponseError(
            "ViViBe completed the export without an audio URL"
        )

    audio_content = provider.download(job_status.audio_url)
    duration_seconds = measure_wav_duration(audio_content)
    subtitle_content = (
        provider.download(job_status.subtitle_url)
        if job_status.subtitle_url
        else None
    )
    if subtitle_content is not None:
        validate_srt(subtitle_content)

    scene_directory = (
        PROJECT_ROOT / "data" / "projects" / project.id / "scenes" / scene.key
    )
    audio_path = scene_directory / "narration.wav"
    subtitle_path = scene_directory / "narration.srt"
    write_bytes_atomically(audio_path, audio_content)
    if subtitle_content is not None:
        write_bytes_atomically(subtitle_path, subtitle_content)
    elif subtitle_path.exists():
        subtitle_path.unlink()

    supersede_completed_assets(session, project.id, scene.id, "narration_audio")
    supersede_completed_assets(session, project.id, scene.id, "narration_subtitle")

    audio_metadata = {
        **asset.metadata_json,
        "provider_state": "completed",
        "mime_type": "audio/wav",
        "duration_seconds": duration_seconds,
        "audio_url_downloaded": True,
        "subtitle_available": subtitle_content is not None,
    }
    asset.local_path = audio_path.relative_to(PROJECT_ROOT).as_posix()
    asset.sha256 = hashlib.sha256(audio_content).hexdigest()
    asset.status = "completed"
    asset.metadata_json = audio_metadata

    write_text_atomically(
        audio_path.with_suffix(".metadata.json"),
        json.dumps(audio_metadata, ensure_ascii=False, indent=2) + "\n",
    )

    if subtitle_content is not None:
        subtitle_asset = Asset(
            project=project,
            scene=scene,
            kind="narration_subtitle",
            local_path=subtitle_path.relative_to(PROJECT_ROOT).as_posix(),
            sha256=hashlib.sha256(subtitle_content).hexdigest(),
            provider=provider.name,
            external_job_id=asset.external_job_id,
            status="completed",
            metadata_json={
                "mime_type": "application/x-subrip",
                "voice_id": asset.metadata_json.get("voice_id"),
            },
        )
        session.add(subtitle_asset)

    scene.duration_seconds = duration_seconds
    scene.status = "audio_ready"


def current_scene_audio(
    session: Session,
    project_id: str,
    scene_id: str,
) -> Asset | None:
    statement = (
        select(Asset)
        .where(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.kind == "narration_audio",
            Asset.status == "completed",
        )
        .order_by(Asset.created_at.desc())
    )
    for asset in session.scalars(statement):
        if (PROJECT_ROOT / asset.local_path).is_file():
            return asset
    return None


def active_scene_audio(
    session: Session,
    project_id: str,
    scene_id: str,
) -> Asset | None:
    statement = (
        select(Asset)
        .where(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.kind == "narration_audio",
            Asset.status.in_(ACTIVE_AUDIO_STATUSES),
        )
        .order_by(Asset.created_at.desc())
    )
    return session.scalar(statement)


def audio_matches(asset: Asset, requested_metadata: dict[str, object]) -> bool:
    return all(
        asset.metadata_json.get(key) == value
        for key, value in requested_metadata.items()
    )


def supersede_completed_assets(
    session: Session,
    project_id: str,
    scene_id: str,
    kind: str,
) -> None:
    assets = session.scalars(
        select(Asset).where(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.kind == kind,
            Asset.status == "completed",
        )
    )
    for previous in assets:
        previous.status = "superseded"


def mark_audio_failed(
    session: Session,
    asset: Asset,
    scene: Scene | None,
    error: str,
) -> None:
    asset.status = "failed"
    asset.metadata_json = {
        **asset.metadata_json,
        "provider_state": "failed",
        "error": error,
    }
    if scene is not None:
        scene.status = "audio_failed"


def require_audio_generation_state(project: Project) -> None:
    if project.status not in {"generating_audio", "rendering", "completed"}:
        raise AudioGenerationStateError(
            "Scene images must be approved before generating audio"
        )
    if not project.scenes:
        raise AudioGenerationStateError("Project has no scenes")


def measure_wav_duration(content: bytes) -> float:
    try:
        with wave.open(io.BytesIO(content), "rb") as audio:
            frame_rate = audio.getframerate()
            frame_count = audio.getnframes()
    except (EOFError, wave.Error) as exc:
        raise SpeechProviderResponseError(
            "ViViBe returned an invalid WAV audio file"
        ) from exc
    if frame_rate <= 0 or frame_count <= 0:
        raise SpeechProviderResponseError(
            "ViViBe returned an empty WAV audio file"
        )
    return round(frame_count / frame_rate, 3)


def validate_srt(content: bytes) -> None:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SpeechProviderResponseError(
            "ViViBe returned a non-UTF-8 subtitle file"
        ) from exc
    if "-->" not in text:
        raise SpeechProviderResponseError(
            "ViViBe returned an invalid SRT subtitle file"
        )


def write_bytes_atomically(destination: Path, content: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(destination)


def write_text_atomically(destination: Path, content: str) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
