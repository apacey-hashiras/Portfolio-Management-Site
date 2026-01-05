from typing import List, Optional
import pandas as pd
from pyxirr import xirr
from sqlmodel import Session, select
from ..models import Fund, Transaction, WaterfallAllocation, TransactionType, PortfolioCompany
import uuid

def calculate_fund_metrics(session: Session, fund_id: uuid.UUID):
    fund = session.get(Fund, fund_id)
    if not fund:
        return None

    # Total Contributed
    contributed_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type == TransactionType.capital_call
    )
    total_contributed = sum(tx.amount for tx in session.exec(contributed_stmt).all())

    # Total Distributions (Gross)
    dist_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type == TransactionType.distribution
    )
    total_distributions = sum(tx.amount for tx in session.exec(dist_stmt).all())

    # Total Fees
    fees_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type.in_([TransactionType.management_fee, TransactionType.other_fee])
    )
    total_fees = sum(tx.amount for tx in session.exec(fees_stmt).all())

    # Fund Unrealized Value
    companies_stmt = select(PortfolioCompany).where(PortfolioCompany.fund_id == fund_id)
    companies = session.exec(companies_stmt).all()
    fund_unrealized_value = sum(
        (c.latest_post_money * c.ownership_pct) if (c.latest_post_money and c.ownership_pct) else 0 
        for c in companies
    )

    # Gross MOIC
    gross_moic = total_distributions / total_contributed if total_contributed > 0 else 0

    # LP Net Metrics (after waterfall)
    waterfall_stmt = select(WaterfallAllocation).where(WaterfallAllocation.fund_id == fund_id)
    waterfall_allocs = session.exec(waterfall_stmt).all()
    lp_total_distributions = sum(a.lp_distribution for a in waterfall_allocs)
    total_gp_carry = sum(a.gp_distribution for a in waterfall_allocs)

    lp_net_moic = (lp_total_distributions + fund_unrealized_value) / total_contributed if total_contributed > 0 else 0

    # IRR Calculation
    # Cashflows for Net IRR:
    # - Capital calls (negative)
    # - Fees (negative)
    # - LP Distributions (positive)
    # - Unrealized value (positive, as of today)
    
    cashflows = []
    dates = []

    # Outflows
    outflows_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type.in_([TransactionType.capital_call, TransactionType.management_fee, TransactionType.other_fee])
    )
    for tx in session.exec(outflows_stmt).all():
        cashflows.append(-tx.amount)
        dates.append(tx.transaction_date)

    # Inflows (LP Share)
    for alloc in waterfall_allocs:
        cashflows.append(alloc.lp_distribution)
        dates.append(alloc.distribution_date)

    # Terminal Value (Unrealized)
    if fund_unrealized_value > 0:
        cashflows.append(fund_unrealized_value)
        dates.append(pd.Timestamp.now().date())

    fund_net_irr = None
    if len(cashflows) > 1:
        try:
            fund_net_irr = xirr(dates, cashflows)
        except:
            fund_net_irr = None

    return {
        "fund_id": fund_id,
        "total_contributed": total_contributed,
        "total_distributions": total_distributions,
        "total_fees": total_fees,
        "gross_moic": round(gross_moic, 3),
        "lp_net_moic": round(lp_net_moic, 4),
        "fund_net_irr": round(fund_net_irr, 4) if fund_net_irr is not None else None,
        "total_gp_carry": total_gp_carry,
        "fund_unrealized_value": fund_unrealized_value
    }
