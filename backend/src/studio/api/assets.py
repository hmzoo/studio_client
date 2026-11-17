from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import storage
from ..database import get_db
from ..domain.models import Asset
from ..schemas.dto import AssetOut

router = APIRouter()


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    a = db.get(Asset, asset_id)
    if a is None:
        raise HTTPException(status_code=404, detail="asset introuvable")
    return a


@router.get("/{asset_id}/content")
def get_asset_content(asset_id: str, db: Session = Depends(get_db)):
    a = db.get(Asset, asset_id)
    if a is None:
        raise HTTPException(status_code=404, detail="asset introuvable")
    try:
        path = storage.resolve(a.local_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(path, media_type=a.mime_type or "application/octet-stream")
