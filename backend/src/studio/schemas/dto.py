"""Schémas Pydantic de l'API du Studio."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class ReferenceCreate(BaseModel):
    kind: str = Field(..., pattern="^(character|environment)$")
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""


class ReferenceOut(BaseModel):
    id: str
    project_id: str
    kind: str
    name: str
    initial_description: str
    approved_description: str | None = None
    media_ids: str = ""


class AssetOut(BaseModel):
    id: str
    project_id: str | None
    kind: str
    origin: str
    mime_type: str
    width: int | None
    height: int | None
    external_id: str | None
    external_url: str | None
    is_simulated: bool
    created_at: datetime


class ProposalOut(BaseModel):
    id: str
    project_id: str
    subject_type: str
    subject_id: str
    content: str
    references: str
    status: str
    validation_comment: str | None = None
    created_at: datetime


class ProposalDecision(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
    comment: str = ""


class GenerationCreate(BaseModel):
    kind: str = Field(..., pattern="^(text|image|video)$")
    request: dict[str, Any]


class GenerationOut(BaseModel):
    id: str
    project_id: str
    kind: str
    status: str
    external_job_id: str | None
    result: Any = None
    error: Any = None
    created_at: datetime
    updated_at: datetime


class TaskOut(BaseModel):
    id: str
    kind: str
    status: str
    attempts: int
    max_attempts: int
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
