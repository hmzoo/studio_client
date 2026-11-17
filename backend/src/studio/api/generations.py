from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..domain.models import Generation
from ..schemas.dto import GenerationCreate, GenerationOut

router = APIRouter()


@router.post("", response_model=GenerationOut)
def create_generation(project_id: str, body: GenerationCreate, db: Session = Depends(get_db)):
    try:
        return services.request_generation(db, project_id, body.kind, body.request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=list[GenerationOut])
def list_generations(project_id: str, db: Session = Depends(get_db)):
    return services.list_generations(db, project_id)


@router.get("/{generation_id}", response_model=GenerationOut)
def get_generation(project_id: str, generation_id: str, db: Session = Depends(get_db)):
    g = db.get(Generation, generation_id)
    if g is None or g.project_id != project_id:
        raise HTTPException(status_code=404, detail="génération introuvable")
    return g
