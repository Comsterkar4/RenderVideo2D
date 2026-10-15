from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.config import VIDEO_LANGUAGE, VISUAL_STYLE

from backend.database import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


scene_characters = Table(
    "scene_characters",
    Base.metadata,
    Column("scene_id", ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True),
    Column("character_id", ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(200))
    story: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default=VIDEO_LANGUAGE)
    aspect_ratio: Mapped[str] = mapped_column(String(8), default="16:9")
    visual_style: Mapped[str] = mapped_column(String(500), default=VISUAL_STYLE)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    characters: Mapped[list["Character"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Character.created_at",
    )
    scenes: Mapped[list["Scene"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Scene.order_index",
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Asset.created_at",
    )


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_characters_project_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    appearance: Mapped[str] = mapped_column(Text)
    prompt_fragment: Mapped[str] = mapped_column(Text)
    voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped[Project] = relationship(back_populates="characters")
    scenes: Mapped[list["Scene"]] = relationship(
        secondary=scene_characters,
        back_populates="characters",
    )
    assets: Mapped[list["Asset"]] = relationship(back_populates="character")


class Scene(Base):
    __tablename__ = "scenes"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_scenes_project_key"),
        UniqueConstraint("project_id", "order_index", name="uq_scenes_project_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(100))
    order_index: Mapped[int] = mapped_column()
    duration_seconds: Mapped[float] = mapped_column(Float)
    location: Mapped[str] = mapped_column(Text, default="")
    narration: Mapped[str] = mapped_column(Text)
    image_prompt: Mapped[str] = mapped_column(Text)
    motion_prompt: Mapped[str] = mapped_column(Text, default="")
    sound_effects: Mapped[list[str]] = mapped_column(JSON, default=list)
    seed: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped[Project] = relationship(back_populates="scenes")
    characters: Mapped[list[Character]] = relationship(
        secondary=scene_characters,
        back_populates="scenes",
    )
    assets: Mapped[list["Asset"]] = relationship(back_populates="scene")

    @property
    def character_ids(self) -> list[str]:
        return [character.key for character in self.characters]


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    character_id: Mapped[str | None] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(50), index=True)
    local_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    external_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped[Project] = relationship(back_populates="assets")
    scene: Mapped[Scene | None] = relationship(back_populates="assets")
    character: Mapped[Character | None] = relationship(back_populates="assets")
