"""Passerelle HTTP vers l'API de génération externe."""
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

from ..config import settings
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


class HttpGenerationGatewayClient:
    """Client HTTP. Normalise les réponses (200/202 acceptés, états conservés)."""

    def __init__(self) -> None:
        if not settings.generation_api_base_url:
            raise GatewayError("GENERATION_API_BASE_URL non configuré")
        self.base = settings.generation_api_base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.generation_connect_timeout, read=settings.generation_read_timeout),
        )

    # --- helpers ------------------------------------------------------------
    def _headers(self) -> dict:
        h = {}
        if settings.generation_api_key:
            scheme = settings.generation_api_auth_scheme or "Bearer"
            h[settings.generation_api_auth_header] = f"{scheme} {settings.generation_api_key}"
        return h

    def _abs(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.base + "/", url.lstrip("/"))

    def _allowed_origin(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        trusted = settings.trusted_media_origins
        if not trusted:
            base_netloc = urlparse(self.base).netloc
            return origin == f"https://{base_netloc}" or origin == f"http://{base_netloc}"
        return origin in trusted

    def _check_origin(self, url: str) -> None:
        if not self._allowed_origin(url):
            raise GatewayError("origine de média non autorisée")

    def _post(self, path: str, json: dict) -> dict:
        r = self._client.post(self._abs(path), json=json, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def _get(self, path: str) -> dict:
        r = self._client.get(self._abs(path), headers=self._headers())
        r.raise_for_status()
        return r.json()

    # --- API ----------------------------------------------------------------
    def get_models(self) -> dict:
        return self._get("/api/v1/models")

    def generate_text(self, req) -> TextResult:
        d = self._post("/api/v1/text", req.to_dict())
        return TextResult(
            text=d.get("text", ""),
            model=d.get("model", ""),
            data=d.get("data"),
            schema_valid=d.get("schema_valid"),
        )

    def generate_image(self, req, async_exec: bool = False) -> GenerationOutcome:
        path = "/api/v1/images" + ("?execution=async" if async_exec else "")
        d = self._post(path, req.to_dict())
        return self._normalize(d)

    def generate_video(self, req, async_exec: bool = False) -> GenerationOutcome:
        path = "/api/v1/videos" + ("?execution=async" if async_exec else "")
        d = self._post(path, req.to_dict())
        return self._normalize(d)

    def _normalize(self, d: dict) -> GenerationOutcome:
        if isinstance(d.get("job_id"), str) and d.get("job_id"):
            return GenerationOutcome(job=JobRef(job_id=d["job_id"], status=d.get("status", "queued")))
        if "images" in d:
            items = [
                ImageItem(
                    url=self._abs(i.get("url", "")),
                    width=i.get("width", 0),
                    height=i.get("height", 0),
                    seed=i.get("seed", -1),
                    prompt=i.get("prompt", ""),
                    model=i.get("model", ""),
                    mode=d.get("mode", "t2i"),
                )
                for i in d.get("images", [])
            ]
            return GenerationOutcome(direct=ImageResult(images=items, mode=d.get("mode", "t2i"), model=d.get("model", "")))
        if "video" in d:
            v = d["video"]
            return GenerationOutcome(direct=VideoResult(
                video=VideoItem(
                    url=self._abs(v.get("url", "")),
                    width=v.get("width", 0), height=v.get("height", 0),
                    frames=v.get("frames", 0), fps=v.get("fps", 24),
                    mode=v.get("mode", "t2v"), model=v.get("model", ""),
                    recipe=v.get("recipe", ""), seed=v.get("seed", -1),
                ),
                model=d.get("model", ""),
            ))
        raise GatewayError("réponse de génération non reconnue")

    def get_job(self, job_id: str) -> JobStatus:
        d = self._get(f"/api/v1/jobs/{job_id}")
        return JobStatus(
            job_id=d.get("job_id", job_id),
            kind=d.get("kind", ""),
            status=d.get("status", "unknown"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            result=d.get("result"),
            error=d.get("error"),
        )

    def upload_asset(self, filename: str, data: bytes) -> AssetMeta:
        r = self._client.post(
            self._abs("/api/v1/assets"),
            files={"file": (filename, data)},
            headers=self._headers(),
        )
        r.raise_for_status()
        d = r.json()
        return AssetMeta(
            asset_id=d.get("asset_id", ""),
            url=self._abs(d.get("url", "")),
            mime_type=d.get("mime_type", ""),
            width=d.get("width"),
            height=d.get("height"),
            created_at=d.get("created_at"),
            original_name=d.get("original_name"),
        )

    def get_asset_content(self, asset_id: str) -> bytes:
        r = self._client.get(self._abs(f"/api/v1/assets/{asset_id}/content"), headers=self._headers())
        r.raise_for_status()
        return r.content

    def download_media(self, url: str) -> bytes:
        """Télécharge un média depuis une URL (avec contrôle d'origine, redirections incluses)."""
        absolute = self._abs(url)
        self._check_origin(absolute)
        with httpx.Client(
            timeout=httpx.Timeout(settings.generation_connect_timeout, read=settings.generation_read_timeout),
            follow_redirects=True,
        ) as c:
            r = c.get(absolute, headers=self._headers())
            r.raise_for_status()
            final = str(r.url)
            self._check_origin(final)  # contrôle après redirections
            return r.content
