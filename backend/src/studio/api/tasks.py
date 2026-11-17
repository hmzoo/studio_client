from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.models import Task
from ..schemas.dto import TaskOut

router = APIRouter()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    t = db.get(Task, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="tâche introuvable")
    return t
