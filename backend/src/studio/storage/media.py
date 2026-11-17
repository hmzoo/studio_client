"""Stockage local des médias (volume persistant), chemins sécurisés."""
from __future__ import annotations

import uuid
from pathlib import Path

from ..config import settings


def save_media(data: bytes, ext: str, project_id: str | None = None) -> str:
    """Écrit un média et renvoie son chemin RELATIF au répertoire de stockage."""
    ext = ("." + ext.lstrip(".")) if ext else ""
    sub = project_id or "misc"
    rel = Path(sub) / f"{uuid.uuid4().hex}{ext}"
    dest = settings.storage_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(rel)


def resolve(rel_path: str) -> Path:
    """Résout un chemin relatif sans autoriser d'échappement du répertoire."""
    p = (settings.storage_dir / rel_path).resolve()
    root = settings.storage_dir.resolve()
    if root not in p.parents and p != root:
        raise ValueError("chemin hors du répertoire de stockage")
    return p


def read(rel_path: str) -> bytes:
    return resolve(rel_path).read_bytes()
