from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import uuid
from ..database import get_session
from .. import crud, schemas

router = APIRouter(tags=["companies"])

@router.get("/api/funds/{fund_id}/companies", response_model=List[schemas.PortfolioCompanyRead])
def read_companies(fund_id: uuid.UUID, session: Session = Depends(get_session)):
    return crud.get_companies(session, fund_id)

@router.post("/api/funds/{fund_id}/companies", response_model=schemas.PortfolioCompanyRead)
def create_company(fund_id: uuid.UUID, company: schemas.PortfolioCompanyCreate, session: Session = Depends(get_session)):
    if company.fund_id != fund_id:
        raise HTTPException(status_code=400, detail="Fund ID mismatch")
    return crud.create_company(session, company)

@router.get("/api/companies/{company_id}", response_model=schemas.PortfolioCompanyRead)
def read_company(company_id: uuid.UUID, session: Session = Depends(get_session)):
    company = session.get(crud.PortfolioCompany, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
