from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..schemas.dto import SceneCreate, SceneOut, ShotCreate, ShotOut, TaskOut

router = APIRouter()


@router.post("/scenes", response_model=SceneOut)
def create_scene(project_id: str, body: SceneCreate, db: Session = Depends(get_db)):
    try:
        return services.create_scene(db, project_id, body.title, body.narrative, body.order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scenes", response_model=list[SceneOut])
def list_scenes(project_id: str, db: Session = Depends(get_db)):
    return services.list_scenes(db, project_id)


@router.post("/scenes/{scene_id}/shots", response_model=ShotOut)
def create_shot(project_id: str, scene_id: str, body: ShotCreate, db: Session = Depends(get_db)):
    try:
        return services.create_shot(db, scene_id, body.action, body.visual_intent, body.order,
                                    body.character_ids, body.environment_ids, body.media_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scenes/{scene_id}/shots", response_model=list[ShotOut])
def list_shots(project_id: str, scene_id: str, db: Session = Depends(get_db)):
    return services.list_shots(db, scene_id)


@router.post("/scenes/{scene_id}/shots/{shot_id}/generate", response_model=TaskOut)
def generate_shot(project_id: str, scene_id: str, shot_id: str, db: Session = Depends(get_db)):
    """Déclenche une génération pilotée par un agent à partir du plan."""
    try:
        return services.request_shot_generation(db, project_id, shot_id, "image")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/scenes/{scene_id}/shots/{shot_id}")
def delete_shot(project_id: str, scene_id: str, shot_id: str, db: Session = Depends(get_db)):
    try:
        services.delete_shot(db, shot_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
