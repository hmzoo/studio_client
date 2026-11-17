"""Point d'entrée de l'API du Studio."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import domain  # noqa: F401 — enregistre les modèles
from .api import assets, chat, completions, generations, projects, references, storyboard, tasks
from .config import settings
from .database import engine
from .domain.models import Base

app = FastAPI(title="Studio Client", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Démo : création du schéma. Le chemin propre est Alembic (voir README).
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True, "gateway_mode": settings.generation_gateway_mode}


@app.get("/api/config")
def config_info():
    return {
        "gateway_mode": settings.generation_gateway_mode,
        "gateway_base_url_configured": bool(settings.generation_api_base_url),
    }


app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(storyboard.router, prefix="/api/projects/{project_id}", tags=["storyboard"])
app.include_router(references.router, prefix="/api/projects/{project_id}/references", tags=["references"])
app.include_router(completions.router, prefix="/api/projects/{project_id}/completions", tags=["completions"])
app.include_router(generations.router, prefix="/api/projects/{project_id}/generations", tags=["generations"])
app.include_router(chat.router, prefix="/api/projects/{project_id}", tags=["chat"])
app.include_router(assets.router, prefix="/api/assets", tags=["assets"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
