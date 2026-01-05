from typing import List, Union
from sqlmodel import Session, select
from .models import Fund, PortfolioCompany, Transaction, WaterfallAllocation, TransactionType
from .schemas import FundCreate, PortfolioCompanyCreate, TransactionCreate
from .logic.waterfall import compute_waterfall
import uuid

# Funds
def get_funds(session: Session):
    return session.exec(select(Fund)).all()

def get_fund(session: Session, fund_id: uuid.UUID):
    return session.get(Fund, fund_id)

def create_fund(session: Session, fund: FundCreate):
    db_fund = Fund.from_orm(fund)
    session.add(db_fund)
    session.commit()
    session.refresh(db_fund)
    return db_fund

# Companies
def get_companies(session: Session, fund_id: uuid.UUID):
    return session.exec(select(PortfolioCompany).where(PortfolioCompany.fund_id == fund_id)).all()

def create_company(session: Session, company: PortfolioCompanyCreate):
    db_company = PortfolioCompany.from_orm(company)
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company

# Transactions
def get_transactions(session: Session, fund_id: uuid.UUID):
    return session.exec(select(Transaction).where(Transaction.fund_id == fund_id)).all()

def create_transaction(session: Session, transaction: Union[TransactionCreate, dict]):
    if isinstance(transaction, dict):
        db_tx = Transaction(**transaction)
    else:
        db_tx = Transaction.from_orm(transaction)
    session.add(db_tx)
    
    # Business Rule: If capital call, update company total_invested
    if db_tx.tx_type == TransactionType.capital_call and db_tx.company_id:
        company = session.get(PortfolioCompany, db_tx.company_id)
        if company:
            company.total_invested += db_tx.amount
            session.add(company)

    session.commit()
    session.refresh(db_tx)

    # Trigger waterfall recompute if distribution
    if db_tx.tx_type == TransactionType.distribution:
        compute_waterfall(session, db_tx.fund_id)

    return db_tx

def get_waterfall(session: Session, fund_id: uuid.UUID):
    return session.exec(select(WaterfallAllocation).where(WaterfallAllocation.fund_id == fund_id).order_by(WaterfallAllocation.distribution_date.asc())).all()
