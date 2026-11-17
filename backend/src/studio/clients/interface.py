"""Contrat de la passerelle de génération (normalisé)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Protocol


class GatewayError(Exception):
    """Erreur normalisée de la passerelle (pas de trace interne exposée)."""


@dataclass
class TextRequest:
    prompt: str
    system: str | None = None
    images: list[str] | None = None
    response_format: dict | None = None
    temperature: float = 0.7
    max_tokens: int = 1024

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class TextResult:
    text: str
    model: str
    data: Any = None
    schema_valid: bool | None = None


@dataclass
class ImageRequest:
    prompt: str
    image: str | None = None
    width: int = 1024
    height: int = 1024
    steps: int = 28
    cfg_scale: float = 1.0
    seed: int = -1

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ImageItem:
    url: str
    width: int
    height: int
    seed: int
    prompt: str
    model: str
    mode: str = "t2i"


@dataclass
class ImageResult:
    images: list[ImageItem]
    mode: str
    model: str


@dataclass
class VideoRequest:
    prompt: str
    refs: list[str]
    width: int = 864
    height: int = 480
    frames: int = 124
    steps: int = 20
    cfg_scale: float = 1.0
    seed: int = -1
    fps: int = 24

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class VideoItem:
    url: str
    width: int
    height: int
    frames: int
    fps: int
    mode: str
    model: str
    recipe: str
    seed: int


@dataclass
class VideoResult:
    video: VideoItem
    model: str


@dataclass
class JobRef:
    job_id: str
    status: str = "queued"


@dataclass
class JobStatus:
    job_id: str
    kind: str
    status: str
    created_at: float | None = None
    updated_at: float | None = None
    result: Any = None
    error: dict | None = None


@dataclass
class AssetMeta:
    asset_id: str
    url: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    created_at: float | None = None
    original_name: str | None = None


@dataclass
class GenerationOutcome:
    """Résultat direct OU référence de tâche (jamais les deux)."""
    direct: ImageResult | VideoResult | None = None
    job: JobRef | None = None


class GenerationGatewayClient(Protocol):
    def get_models(self) -> dict: ...

    def generate_text(self, req: TextRequest) -> TextResult: ...

    def generate_image(self, req: ImageRequest, async_exec: bool = False) -> GenerationOutcome: ...

    def generate_video(self, req: VideoRequest, async_exec: bool = False) -> GenerationOutcome: ...

    def get_job(self, job_id: str) -> JobStatus: ...

    def upload_asset(self, filename: str, data: bytes) -> AssetMeta: ...

    def get_asset_content(self, asset_id: str) -> bytes: ...

    def download_media(self, url: str) -> bytes: ...
