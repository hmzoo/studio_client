from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..application import services
from ..database import get_db
from ..schemas.dto import ProposalDecision, ProposalOut

router = APIRouter()


@router.get("", response_model=list[ProposalOut])
def list_proposals(project_id: str, db: Session = Depends(get_db)):
    return services.list_proposals(db, project_id)


@router.post("/{proposal_id}/decision", response_model=ProposalOut)
def decide(project_id: str, proposal_id: str, body: ProposalDecision, db: Session = Depends(get_db)):
    try:
        return services.decide_proposal(db, project_id, proposal_id, body.status, body.comment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
