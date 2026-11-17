from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..schemas.dto import AssetOut, ReferenceCreate, ReferenceOut, TaskOut

router = APIRouter()


@router.post("", response_model=ReferenceOut)
def create_reference(project_id: str, body: ReferenceCreate, db: Session = Depends(get_db)):
    try:
        return services.create_reference(db, project_id, body.kind, body.name, body.description)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=list[ReferenceOut])
def list_references(project_id: str, kind: str = Query(...), db: Session = Depends(get_db)):
    if kind not in ("character", "environment"):
        raise HTTPException(status_code=400, detail="kind doit être character ou environment")
    return services.list_references(db, project_id, kind)


@router.post("/{kind}/{ref_id}/import", response_model=AssetOut)
async def import_image(project_id: str, kind: str, ref_id: str,
                       file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    try:
        return services.import_reference_image(db, project_id, kind, ref_id, file.filename or "ref.png", data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/{kind}/{ref_id}/analyze", response_model=TaskOut)
def analyze(project_id: str, kind: str, ref_id: str, db: Session = Depends(get_db)):
    try:
        return services.request_analysis(db, project_id, kind, ref_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
