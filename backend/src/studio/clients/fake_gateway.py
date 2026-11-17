"""Passerelle simulée (mode démonstration). Aucun service réel appelé."""
from __future__ import annotations

import base64
import time
import uuid

from .interface import (
    AssetMeta,
    GatewayError,
    GenerationOutcome,
    ImageItem,
    ImageResult,
    JobRef,
    JobStatus,
    TextResult,
    VideoItem,
    VideoResult,
)

# PNG 1x1 transparent (média simulé identifiable)
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _minimal(schema: dict):
    """Instance minimale valide pour un schéma simple (pas de oneOf/anyOf)."""
    t = schema.get("type", "object")
    if t == "object":
        out = {}
        for name, prop in (schema.get("properties") or {}).items():
            if name in (schema.get("required") or []):
                out[name] = _minimal(prop)
        return out
    if t == "array":
        return []
    if t == "string":
        return "simulé"
    if t in ("integer", "number"):
        return 0
    if t == "boolean":
        return True
    return None


class FakeGenerationGatewayClient:
    """Même interface que le client HTTP, avec des résultats simulés."""

    simulated = True

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._assets: dict[str, AssetMeta] = {}

    def get_models(self) -> dict:
        return {
            "llm": {"model": "fake-llm", "vision": True, "structured_output": True},
            "image": {"model": "fake-image", "editing": True},
            "video": {"model": "fake-video", "ref2v": True},
        }

    def generate_text(self, req) -> TextResult:
        rf = req.response_format
        if rf and rf.get("type") == "json_schema":
            data = _minimal(rf.get("json_schema", {}).get("schema", rf.get("schema", {})))
            if isinstance(data, dict) and "description" in data:
                data["description"] = "Référence simulée : description générée par le client fake."
            return TextResult(text=repr(data), model="fake-llm", data=data, schema_valid=True)
        return TextResult(text="Texte simulé (client fake).", model="fake-llm", data=None, schema_valid=None)

    def generate_image(self, req, async_exec: bool = False) -> GenerationOutcome:
        url = f"fake://media/img_{uuid.uuid4().hex[:8]}.png"
        if async_exec:
            job_id = uuid.uuid4().hex[:12]
            self._jobs[job_id] = {
                "kind": "image", "status": "queued", "created_at": time.time(),
                "result": {
                    "images": [{"url": url, "width": req.width, "height": req.height,
                                "seed": 123, "prompt": req.prompt, "model": "fake-image",
                                "mode": "t2i"}],
                    "mode": "t2i", "model": "fake-image",
                },
            }
            return GenerationOutcome(job=JobRef(job_id=job_id, status="queued"))
        return GenerationOutcome(direct=ImageResult(
            images=[ImageItem(url=url, width=req.width, height=req.height, seed=123,
                              prompt=req.prompt, model="fake-image", mode="t2i")],
            mode="t2i", model="fake-image",
        ))

    def generate_video(self, req, async_exec: bool = False) -> GenerationOutcome:
        job_id = uuid.uuid4().hex[:12]
        self._jobs[job_id] = {
            "kind": "video", "status": "queued", "created_at": time.time(),
            # Pas de fichier vidéo de démonstration : échec contrôlé.
            "error": {"code": "generation_failed", "message": "pas de vidéo de démonstration (client fake)"},
        }
        return GenerationOutcome(job=JobRef(job_id=job_id, status="queued"))

    def get_job(self, job_id: str) -> JobStatus:
        j = self._jobs.get(job_id)
        if j is None:
            raise GatewayError("job inconnu (fake)")
        if j["kind"] == "image":
            j["status"] = "succeeded"
            return JobStatus(job_id=job_id, kind="image", status="succeeded",
                             result=j.get("result"), error=None, created_at=j["created_at"])
        # vidéo : échec contrôlé
        return JobStatus(job_id=job_id, kind="video", status="failed",
                         result=None, error=j.get("error"), created_at=j["created_at"])

    def upload_asset(self, filename: str, data: bytes) -> AssetMeta:
        asset_id = uuid.uuid4().hex[:12]
        mime = "image/png" if filename.lower().endswith(".png") else "application/octet-stream"
        meta = AssetMeta(asset_id=asset_id, url=f"fake://asset/{asset_id}", mime_type=mime,
                         original_name=filename, created_at=time.time())
        self._assets[asset_id] = meta
        return meta

    def get_asset_content(self, asset_id: str) -> bytes:
        return _TINY_PNG

    def download_media(self, url: str) -> bytes:
        if url.startswith("fake://media/") or url.startswith("fake://asset/"):
            return _TINY_PNG
        raise GatewayError("média simulé indisponible (vidéo)")
