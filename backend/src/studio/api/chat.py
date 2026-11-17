"""Chat de pilotage de l'orchestrateur."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..schemas.dto import ChatRequest

router = APIRouter()


@router.post("/chat")
def chat(project_id: str, body: ChatRequest, db: Session = Depends(get_db)):
    try:
        return services.chat_orchestrator(db, project_id, body.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
