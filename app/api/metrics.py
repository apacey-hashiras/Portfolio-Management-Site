from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import uuid
from ..database import get_session
from .. import crud, schemas
from ..logic.metrics import calculate_fund_metrics

router = APIRouter(prefix="/api/funds", tags=["metrics"])

@router.get("/{fund_id}/metrics", response_model=schemas.FundMetrics)
def read_fund_metrics(fund_id: uuid.UUID, session: Session = Depends(get_session)):
    metrics = calculate_fund_metrics(session, fund_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Fund not found")
    return metrics

@router.get("/{fund_id}/waterfall", response_model=List[schemas.WaterfallAllocationRead])
def read_waterfall(fund_id: uuid.UUID, session: Session = Depends(get_session)):
    return crud.get_waterfall(session, fund_id)
