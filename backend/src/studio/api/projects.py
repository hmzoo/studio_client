from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..schemas.dto import AssetOut, ProjectCreate, ProjectOut

router = APIRouter()


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    return services.create_project(db, body.name, body.description)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return services.list_projects(db)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    try:
        return services.get_project(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/assets", response_model=list[AssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return services.list_assets(db, project_id)
