"""Configuration du Studio (variables d'environnement)."""
from __future__ import annotations

import os
from pathlib import Path


def _f(name: str, default: str) -> str:
    return os.getenv(name, default)


class Settings:
    app_name: str = "studio-client"

    # Base de données (PostgreSQL en compose, SQLite possible pour les tests)
    database_url: str = _f("DATABASE_URL", "postgresql+psycopg://studio:studio@postgres:5432/studio")

    # Passerelle de génération (API externe)
    generation_gateway_mode: str = _f("GENERATION_GATEWAY_MODE", "fake")  # fake | http
    generation_api_base_url: str = _f("GENERATION_API_BASE_URL", "")
    generation_api_key: str = _f("GENERATION_API_KEY", "")
    generation_api_auth_header: str = _f("GENERATION_API_AUTH_HEADER", "Authorization")
    generation_api_auth_scheme: str = _f("GENERATION_API_AUTH_SCHEME", "Bearer")
    generation_connect_timeout: float = float(_f("GENERATION_CONNECT_TIMEOUT", "10"))
    generation_read_timeout: float = float(_f("GENERATION_READ_TIMEOUT", "600"))
    generation_poll_interval: float = float(_f("GENERATION_POLL_INTERVAL", "2.0"))
    generation_max_track_seconds: float = float(_f("GENERATION_MAX_TRACK_SECONDS", "600"))

    # Origines de confiance pour les téléchargements de médias (séparées par des virgules)
    trusted_media_origins: list[str] = [
        o for o in _f("TRUSTED_MEDIA_ORIGINS", "").split(",") if o
    ]

    # Stockage local des médias (volume persistant)
    storage_dir: Path = Path(_f("STUDIO_STORAGE_DIR", "./media"))

    def __post_init__(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
