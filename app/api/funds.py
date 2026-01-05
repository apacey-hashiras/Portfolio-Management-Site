from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import uuid
from ..database import get_session
from .. import crud, schemas

router = APIRouter(prefix="/api/funds", tags=["funds"])

@router.post("/", response_model=schemas.FundRead)
def create_fund(fund: schemas.FundCreate, session: Session = Depends(get_session)):
    return crud.create_fund(session, fund)

@router.get("/", response_model=List[schemas.FundRead])
def read_funds(session: Session = Depends(get_session)):
    return crud.get_funds(session)

@router.get("/{fund_id}", response_model=schemas.FundRead)
def read_fund(fund_id: uuid.UUID, session: Session = Depends(get_session)):
    fund = crud.get_fund(session, fund_id)
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    return fund
