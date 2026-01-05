from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import uuid
from ..database import get_session
from .. import crud, schemas

router = APIRouter(tags=["transactions"])

@router.get("/api/funds/{fund_id}/transactions", response_model=List[schemas.TransactionRead])
def read_transactions(fund_id: uuid.UUID, session: Session = Depends(get_session)):
    return crud.get_transactions(session, fund_id)

@router.post("/api/funds/{fund_id}/transactions", response_model=schemas.TransactionRead)
def create_transaction(fund_id: uuid.UUID, transaction: schemas.TransactionCreate, session: Session = Depends(get_session)):
    if transaction.fund_id is None:
        transaction.fund_id = fund_id
    elif transaction.fund_id != fund_id:
        raise HTTPException(status_code=400, detail="Fund ID mismatch")
    return crud.create_transaction(session, transaction)
