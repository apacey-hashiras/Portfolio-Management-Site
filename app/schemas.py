from typing import List, Optional, Dict, Any
from sqlmodel import SQLModel, Field
from .models import FundBase, PortfolioCompanyBase, TransactionBase, WaterfallAllocationBase
import uuid

class FundCreate(FundBase):
    pass

class FundRead(FundBase):
    id: uuid.UUID

class PortfolioCompanyCreate(PortfolioCompanyBase):
    pass

class PortfolioCompanyRead(PortfolioCompanyBase):
    id: uuid.UUID

class TransactionCreate(TransactionBase):
    pass

class TransactionRead(TransactionBase):
    id: uuid.UUID

class WaterfallAllocationRead(WaterfallAllocationBase):
    id: uuid.UUID

class FundMetrics(SQLModel):
    fund_id: uuid.UUID
    total_contributed: float
    total_distributions: float
    total_fees: float
    gross_moic: float
    lp_net_moic: float
    fund_gross_irr: Optional[float] = None
    fund_net_irr: Optional[float] = None
    total_gp_carry: float
    fund_unrealized_value: float
    # Standard Industry Metrics
    tvpi: float = 0.0
    dpi: float = 0.0
    rvpi: float = 0.0
    moic: float = 0.0
    realized_gains: float = 0.0
    unrealized_gains: float = 0.0
