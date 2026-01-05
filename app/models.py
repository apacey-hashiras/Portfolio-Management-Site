from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON
import uuid

class TransactionType(str, Enum):
    capital_call = "capital_call"
    management_fee = "management_fee"
    other_fee = "other_fee"
    distribution = "distribution"
    carry_payment = "carry_payment"
    other = "other"

class FundBase(SQLModel):
    name: str
    fund_code: Optional[str] = None
    manager_id: Optional[uuid.UUID] = None
    fund_start_date: date
    fund_tenor_years: int = 10
    total_commitment: float
    management_fee_pct: float
    carry_pct: float
    investment_period_years: int = 5
    fee_calc_method: str = "committed"
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class Fund(FundBase, table=True):
    __tablename__ = "funds"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    companies: List["PortfolioCompany"] = Relationship(back_populates="fund")
    transactions: List["Transaction"] = Relationship(back_populates="fund")

class PortfolioCompanyBase(SQLModel):
    fund_id: uuid.UUID = Field(foreign_key="funds.id")
    name: str
    stage: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[str] = None
    initial_investment_amount: float = 0
    initial_investment_date: Optional[date] = None
    follow_on_reserved_amount: float = 0
    is_follow_on_used: bool = False
    total_invested: float = 0
    ownership_pct: Optional[float] = None
    latest_post_money: Optional[float] = None
    last_round_date: Optional[date] = None
    status: str = "active"
    exit_date: Optional[date] = None
    exit_proceeds: float = 0
    description: Optional[str] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class PortfolioCompany(PortfolioCompanyBase, table=True):
    __tablename__ = "portfolio_companies"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    fund: Fund = Relationship(back_populates="companies")
    transactions: List["Transaction"] = Relationship(back_populates="company")

class TransactionBase(SQLModel):
    fund_id: uuid.UUID = Field(foreign_key="funds.id")
    company_id: Optional[uuid.UUID] = Field(default=None, foreign_key="portfolio_companies.id")
    transaction_date: date
    amount: float
    tx_type: TransactionType
    reference: Optional[str] = None
    related_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

class Transaction(TransactionBase, table=True):
    __tablename__ = "transactions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    fund: Fund = Relationship(back_populates="transactions")
    company: Optional[PortfolioCompany] = Relationship(back_populates="transactions")

class WaterfallAllocationBase(SQLModel):
    fund_id: uuid.UUID = Field(foreign_key="funds.id")
    transaction_id: uuid.UUID = Field(foreign_key="transactions.id")
    distribution_date: date
    gross: float
    roc_paid: float
    profit_portion: float
    lp_share: float
    gp_share: float
    lp_distribution: float
    gp_distribution: float
    remaining_capital_to_return: float

class WaterfallAllocation(WaterfallAllocationBase, table=True):
    __tablename__ = "waterfall_allocations"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
