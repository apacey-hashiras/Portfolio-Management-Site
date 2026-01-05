from typing import List
from sqlmodel import Session, select
from ..models import Fund, Transaction, WaterfallAllocation, TransactionType
import uuid

def compute_waterfall(session: Session, fund_id: uuid.UUID):
    # 1. Get fund details
    fund = session.get(Fund, fund_id)
    if not fund:
        return

    # 2. Calculate Total Contributed (actual invested amounts)
    # According to readme: Total_Contributed = SUM(portfolio_companies.total_invested)
    # Or transaction-based: SUM(CASE WHEN tx.tx_type='capital_call' THEN tx.amount ELSE 0 END)
    # We'll use the transaction-based approach for better audit trail
    total_contributed_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type == TransactionType.capital_call
    )
    capital_calls = session.exec(total_contributed_stmt).all()
    total_contributed = sum(tx.amount for tx in capital_calls)

    # 3. Get all distributions ordered by date
    distributions_stmt = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.tx_type == TransactionType.distribution
    ).order_by(Transaction.transaction_date.asc())
    distributions = session.exec(distributions_stmt).all()

    # 4. Clear existing waterfall allocations for this fund
    existing_allocations_stmt = select(WaterfallAllocation).where(WaterfallAllocation.fund_id == fund_id)
    existing_allocations = session.exec(existing_allocations_stmt).all()
    for alloc in existing_allocations:
        session.delete(alloc)
    session.commit()

    # 5. Run Waterfall Algorithm
    remaining_capital_to_return = total_contributed
    carry_pct = fund.carry_pct

    for dist in distributions:
        gross = dist.amount
        
        roc_paid = min(remaining_capital_to_return, gross)
        remaining_capital_to_return -= roc_paid
        profit_portion = gross - roc_paid

        gp_share = round(profit_portion * carry_pct, 2)
        lp_share_profit = profit_portion - gp_share

        lp_distribution = roc_paid + lp_share_profit
        gp_distribution = gp_share

        allocation = WaterfallAllocation(
            fund_id=fund_id,
            transaction_id=dist.id,
            distribution_date=dist.transaction_date,
            gross=gross,
            roc_paid=roc_paid,
            profit_portion=profit_portion,
            lp_share=lp_share_profit, # profit share for LP
            gp_share=gp_share,
            lp_distribution=lp_distribution,
            gp_distribution=gp_distribution,
            remaining_capital_to_return=remaining_capital_to_return
        )
        session.add(allocation)

    session.commit()
