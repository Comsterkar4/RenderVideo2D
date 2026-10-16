from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import wave
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import PROJECT_ROOT
from backend.models import Asset, Project
from backend.services.audio_service import current_scene_audio
from backend.services.image_service import current_scene_image


RENDER_LOCK = Lock()
RENDER_QUALITIES = {"preview", "final"}
VIDEO_FPS = 24
TIMING_PATTERN = re.compile(
    r"(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2}),(?P<milliseconds>\d{3})"
)


class VideoRenderError(RuntimeError):
    pass


class VideoRenderInputError(VideoRenderError):
    pass


class VideoRenderToolError(VideoRenderError):
    pass


def render_project(
    session: Session,
    project: Project,
    quality: Literal["preview", "final"],
) -> Asset:
    if quality not in RENDER_QUALITIES:
        raise VideoRenderInputError(f"Unsupported render quality: {quality}")
    if not project.scenes:
        raise VideoRenderInputError("Project has no scenes")
    if project.status not in {"rendering", "completed"}:
        raise VideoRenderInputError(
            "Scene audio must be ready before rendering the video"
        )

    ffmpeg = find_ffmpeg()
    project_directory = PROJECT_ROOT / "data" / "projects" / project.id

    timeline = build_timeline(session, project, quality)
    timeline_path = project_directory / "timeline.json"
    write_json_atomically(timeline_path, timeline)

    previous_status = project.status
    project.status = "rendering"
    session.commit()

    try:
        output_path = render_timeline(
            project_directory=project_directory,
            timeline=timeline,
            quality=quality,
            ffmpeg=ffmpeg,
        )
        asset = save_render_asset(
            session=session,
            project=project,
            output_path=output_path,
            timeline=timeline,
            quality=quality,
        )
        project.status = "completed"
        session.commit()
        return asset
    except Exception:
        project.status = previous_status
        session.commit()
        raise


def build_timeline(
    session: Session,
    project: Project,
    quality: Literal["preview", "final"],
) -> dict[str, Any]:
    width, height = output_dimensions(project.aspect_ratio, quality)
    project_directory = PROJECT_ROOT / "data" / "projects" / project.id
    timeline_scenes: list[dict[str, Any]] = []
    cumulative_offset = 0.0
    has_subtitles = False

    for index, scene in enumerate(project.scenes):
        image_asset = current_scene_image(session, project.id, scene.id)
        audio_asset = current_scene_audio(session, project.id, scene.id)
        subtitle_asset = current_scene_subtitle(session, project.id, scene.id)
        if image_asset is None:
            raise VideoRenderInputError(f"Scene {scene.key} has no completed image")
        if audio_asset is None:
            raise VideoRenderInputError(f"Scene {scene.key} has no completed narration")

        image_path = checked_project_path(project_directory, image_asset.local_path)
        audio_path = checked_project_path(project_directory, audio_asset.local_path)
        duration_seconds = measure_wav_duration(audio_path)
        scene.duration_seconds = duration_seconds
        subtitle_path = (
            checked_project_path(project_directory, subtitle_asset.local_path)
            if subtitle_asset is not None
            else None
        )
        if subtitle_path is not None:
            has_subtitles = True

        timeline_scenes.append(
            {
                "id": scene.key,
                "image": image_path.relative_to(project_directory).as_posix(),
                "audio": audio_path.relative_to(project_directory).as_posix(),
                "subtitle": (
                    subtitle_path.relative_to(project_directory).as_posix()
                    if subtitle_path is not None
                    else None
                ),
                "duration_seconds": duration_seconds,
                "animation": "slow_zoom_in" if index % 2 == 0 else "slow_zoom_out",
                "transition": "cut",
            }
        )
        cumulative_offset += duration_seconds

    session.commit()
    return {
        "width": width,
        "height": height,
        "fps": VIDEO_FPS,
        "quality": quality,
        "duration_seconds": round(cumulative_offset, 3),
        "scenes": timeline_scenes,
        "subtitles": "subtitles/final.ass" if has_subtitles else None,
        "output": f"renders/{quality}.mp4",
    }


def render_timeline(
    *,
    project_directory: Path,
    timeline: dict[str, Any],
    quality: Literal["preview", "final"],
    ffmpeg: str,
) -> Path:
    temporary_directory = project_directory / ".render-tmp"
    if temporary_directory.exists():
        shutil.rmtree(temporary_directory)
    temporary_directory.mkdir(parents=True, exist_ok=True)
    output_path = project_directory / str(timeline["output"])
    joined_path = temporary_directory / "joined.mp4"
    concat_path = temporary_directory / "concat.txt"
    subtitle_path = project_directory / "subtitles" / "final.ass"
    try:
        subtitle_content = build_final_ass(project_directory, timeline)
        if subtitle_content:
            write_text_atomically(subtitle_path, subtitle_content)
        elif subtitle_path.exists():
            subtitle_path.unlink()

        clip_paths: list[Path] = []
        for index, scene in enumerate(timeline["scenes"]):
            clip_path = temporary_directory / f"scene-{index:04d}.mp4"
            render_scene_clip(
                ffmpeg=ffmpeg,
                image_path=project_directory / scene["image"],
                audio_path=project_directory / scene["audio"],
                output_path=clip_path,
                width=int(timeline["width"]),
                height=int(timeline["height"]),
                fps=int(timeline["fps"]),
                animation=str(scene["animation"]),
                quality=quality,
            )
            clip_paths.append(clip_path)

        write_concat_file(concat_path, clip_paths)
        run_ffmpeg(
            ffmpeg,
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_path),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(joined_path),
            ],
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_output = temporary_directory / "output.mp4"
        if subtitle_content:
            run_ffmpeg(
                ffmpeg,
                [
                    "-i",
                    str(joined_path),
                    "-vf",
                    f"subtitles=filename='{escape_filter_path(subtitle_path)}'",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast" if quality == "preview" else "medium",
                    "-crf",
                    "28" if quality == "preview" else "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "copy",
                    "-movflags",
                    "+faststart",
                    str(temporary_output),
                ],
            )
        else:
            shutil.copyfile(joined_path, temporary_output)
        temporary_output.replace(output_path)
        return output_path
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)


def render_scene_clip(
    *,
    ffmpeg: str,
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
    animation: str,
    quality: Literal["preview", "final"],
) -> None:
    zoom_expression = (
        "min(zoom+0.0005,1.08)"
        if animation == "slow_zoom_in"
        else "max(1.0,zoom-0.0005)"
    )
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='{zoom_expression}':d=1:s={width}x{height}:fps={fps},"
        "format=yuv420p"
    )
    run_ffmpeg(
        ffmpeg,
        [
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            f"[0:v]{video_filter}[v]",
            "-map",
            "[v]",
            "-map",
            "1:a:0",
            "-shortest",
            "-af",
            "aresample=async=1:first_pts=0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast" if quality == "preview" else "medium",
            "-crf",
            "28" if quality == "preview" else "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
    )


def save_render_asset(
    *,
    session: Session,
    project: Project,
    output_path: Path,
    timeline: dict[str, Any],
    quality: str,
) -> Asset:
    previous_assets = session.scalars(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.kind == "render_video",
            Asset.status == "completed",
        )
    )
    for previous in previous_assets:
        if previous.metadata_json.get("quality") == quality:
            previous.status = "superseded"

    asset = Asset(
        project=project,
        kind="render_video",
        local_path=output_path.relative_to(PROJECT_ROOT).as_posix(),
        sha256=sha256_file(output_path),
        provider="ffmpeg",
        model="libx264",
        status="completed",
        metadata_json={
            "mime_type": "video/mp4",
            "quality": quality,
            "width": timeline["width"],
            "height": timeline["height"],
            "fps": timeline["fps"],
            "duration_seconds": timeline["duration_seconds"],
            "scene_count": len(timeline["scenes"]),
            "timeline_path": "timeline.json",
            "subtitle_burned": bool(timeline["subtitles"]),
        },
    )
    session.add(asset)
    session.flush()
    return asset


def current_scene_subtitle(
    session: Session,
    project_id: str,
    scene_id: str,
) -> Asset | None:
    statement = (
        select(Asset)
        .where(
            Asset.project_id == project_id,
            Asset.scene_id == scene_id,
            Asset.kind == "narration_subtitle",
            Asset.status == "completed",
        )
        .order_by(Asset.created_at.desc())
    )
    for asset in session.scalars(statement):
        if (PROJECT_ROOT / asset.local_path).is_file():
            return asset
    return None


def output_dimensions(aspect_ratio: str, quality: str) -> tuple[int, int]:
    base = {
        "preview": {"16:9": (960, 540), "9:16": (540, 960), "1:1": (720, 720)},
        "final": {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)},
    }
    try:
        return base[quality][aspect_ratio]
    except KeyError as exc:
        raise VideoRenderInputError(
            f"Unsupported aspect ratio or render quality: {aspect_ratio}, {quality}"
        ) from exc


def find_ffmpeg() -> str:
    configured = os.environ.get("FFMPEG_BIN")
    executable = shutil.which(configured or "ffmpeg")
    if executable is not None:
        return executable

    if configured is None:
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            pass

    raise VideoRenderToolError(
        "FFmpeg is not available. Install it locally or set FFMPEG_BIN to its path."
    )


def run_ffmpeg(ffmpeg: str, arguments: list[str]) -> None:
    completed = subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise VideoRenderToolError(
            f"FFmpeg failed with exit code {completed.returncode}: {detail[-1200:]}"
        )


def checked_project_path(project_directory: Path, relative_path: str) -> Path:
    path = (PROJECT_ROOT / relative_path).resolve()
    project_root = project_directory.resolve()
    if not path.is_relative_to(project_root) or not path.is_file():
        raise VideoRenderInputError(f"Render input file is missing: {relative_path}")
    return path


def checked_project_relative_path(project_directory: Path, relative_path: str) -> Path:
    path = (project_directory / relative_path).resolve()
    project_root = project_directory.resolve()
    if not path.is_relative_to(project_root) or not path.is_file():
        raise VideoRenderInputError(f"Render input file is missing: {relative_path}")
    return path


def measure_wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as audio:
            frame_rate = audio.getframerate()
            frame_count = audio.getnframes()
    except (OSError, EOFError, wave.Error) as exc:
        raise VideoRenderInputError(f"Invalid narration WAV: {path.name}") from exc
    if frame_rate <= 0 or frame_count <= 0:
        raise VideoRenderInputError(f"Empty narration WAV: {path.name}")
    return round(frame_count / frame_rate, 3)


def build_final_ass(project_directory: Path, timeline: dict[str, Any]) -> str:
    width = int(timeline["width"])
    height = int(timeline["height"])
    font_size = max(24, round(width * 0.045))
    margin = max(36, round(height * 0.08))
    max_chars = max(30, min(48, round(width / 14)))
    dialogues: list[str] = []
    offset_ms = 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,{font_size},&H0000FFFF,&H00B8B8B8,&H00101010,&H90000000,0,0,0,0,100,100,0,0,1,2,1,2,32,32,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for scene in timeline["scenes"]:
        subtitle = scene.get("subtitle")
        if subtitle:
            path = checked_project_relative_path(project_directory, subtitle)
            for start_ms, end_ms, text in parse_srt_cues(
                path.read_text(encoding="utf-8")
            ):
                groups = split_caption_words(text, max_chars)
                group_durations = allocate_durations(
                    end_ms - start_ms,
                    [sum(word_weight(word) for word in group) for group in groups],
                )
                cursor = start_ms + offset_ms
                for group, duration_ms in zip(groups, group_durations):
                    group_end = cursor + duration_ms
                    dialogues.append(
                        "Dialogue: 0,"
                        f"{format_ass_timestamp(cursor)},"
                        f"{format_ass_timestamp(group_end)},"
                        f"Karaoke,,0,0,0,,{karaoke_text(group, duration_ms)}"
                    )
                    cursor = group_end
        offset_ms += round(float(scene["duration_seconds"]) * 1000)

    return header + "\n".join(dialogues) + ("\n" if dialogues else "")


def parse_srt_cues(content: str) -> list[tuple[int, int, str]]:
    cues: list[tuple[int, int, str]] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = block.splitlines()
        timing_index = next(
            (index for index, line in enumerate(lines) if " --> " in line),
            None,
        )
        if timing_index is None:
            continue
        start, end = lines[timing_index].split(" --> ", 1)
        text = " ".join(line.strip() for line in lines[timing_index + 1:] if line.strip())
        if text:
            cues.append(
                (
                    parse_srt_timestamp(start),
                    parse_srt_timestamp(end),
                    text,
                )
            )
    return cues


def split_caption_words(text: str, max_chars: int) -> list[list[str]]:
    words = text.split()
    groups: list[list[str]] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        proposed_length = current_length + len(word) + (1 if current else 0)
        if current and proposed_length > max_chars:
            groups.append(current)
            current = []
            current_length = 0
        current.append(word)
        current_length += len(word) + (1 if current_length else 0)
    if current:
        groups.append(current)
    return groups or [[]]


def word_weight(word: str) -> int:
    return max(1, len(re.sub(r"[^\wÀ-ỹ]", "", word, flags=re.UNICODE)))


def allocate_durations(total_ms: int, weights: list[int]) -> list[int]:
    if not weights:
        return []
    total_ms = max(len(weights), total_ms)
    total_weight = sum(weights)
    durations = [
        max(1, round(total_ms * weight / total_weight))
        for weight in weights
    ]
    durations[-1] += total_ms - sum(durations)
    return durations


def karaoke_text(words: list[str], duration_ms: int) -> str:
    total_units = max(len(words), round(duration_ms / 10))
    weights = [word_weight(word) for word in words]
    units = allocate_durations(total_units, weights)
    return " ".join(
        f"{{\\kf{max(1, word_units)}}}{escape_ass_text(word)}"
        for word, word_units in zip(words, units)
    )


def escape_ass_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def format_ass_timestamp(milliseconds: int) -> str:
    milliseconds = max(0, milliseconds)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{millis // 10:02d}"


def parse_srt_timestamp(value: str) -> int:
    match = TIMING_PATTERN.fullmatch(value.strip())
    if match is None:
        raise VideoRenderInputError(f"Invalid SRT timestamp: {value}")
    return (
        int(match["hours"]) * 3_600_000
        + int(match["minutes"]) * 60_000
        + int(match["seconds"]) * 1_000
        + int(match["milliseconds"])
    )


def write_concat_file(destination: Path, paths: list[Path]) -> None:
    content = "\n".join(f"file '{escape_concat_path(path)}'" for path in paths) + "\n"
    write_text_atomically(destination, content)


def escape_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def escape_filter_path(path: Path) -> str:
    return (
        str(path)
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def write_json_atomically(destination: Path, value: dict[str, Any]) -> None:
    write_text_atomically(
        destination,
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
    )


def write_text_atomically(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
