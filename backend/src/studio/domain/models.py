"""Entités métier (SQLAlchemy 2.0). Identifiants locaux stables (uuid hex)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    characters: Mapped[list["Character"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    environments: Mapped[list["Environment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    generations: Mapped[list["Generation"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    initial_description: Mapped[str] = mapped_column(Text, default="")
    approved_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="characters")
    media_ids: Mapped[str] = mapped_column(Text, default="")  # ids d'assets sélectionnés (csv)

    @property
    def kind(self) -> str:
        return "character"


class Environment(Base):
    __tablename__ = "environments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    initial_description: Mapped[str] = mapped_column(Text, default="")
    approved_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="environments")
    media_ids: Mapped[str] = mapped_column(Text, default="")

    @property
    def kind(self) -> str:
        return "environment"


class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200), default="")
    narrative: Mapped[str] = mapped_column(Text, default="")

    project: Mapped[Project] = relationship(back_populates="scenes")
    shots: Mapped[list["Shot"]] = relationship(back_populates="scene", cascade="all, delete-orphan")


class Shot(Base):
    __tablename__ = "shots"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[str] = mapped_column(Text, default="")
    visual_intent: Mapped[str] = mapped_column(Text, default="")
    character_ids: Mapped[str] = mapped_column(Text, default="")
    environment_ids: Mapped[str] = mapped_column(Text, default="")
    media_ids: Mapped[str] = mapped_column(Text, default="")

    scene: Mapped[Scene] = relationship(back_populates="shots")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default="image")  # image | video | file
    origin: Mapped[str] = mapped_column(String(20), default="local")  # local | gateway
    local_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100), default="")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_simulated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CompletionProposal(Base):
    __tablename__ = "completion_proposals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    subject_type: Mapped[str] = mapped_column(String(20))  # character | environment
    subject_id: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text, default="")
    references: Mapped[str] = mapped_column(Text, default="")  # json list
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    validation_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Generation(Base):
    __tablename__ = "generations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # text | image | video
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|needs_reconciliation|succeeded|failed
    request_snapshot: Mapped[str] = mapped_column(Text, default="")  # json, instantané exact
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # json
    error: Mapped[str | None] = mapped_column(Text, nullable=True)  # json normalisée
    previous_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    project: Mapped[Project] = relationship(back_populates="generations")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    kind: Mapped[str] = mapped_column(String(30))  # analyze_reference | generate_image | ...
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|succeeded|failed|needs_reconciliation
    payload: Mapped[str] = mapped_column(Text, default="{}")  # json
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
