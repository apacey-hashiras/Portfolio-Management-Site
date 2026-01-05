from sqlmodel import Session, create_engine, SQLModel
from app.models import Fund, PortfolioCompany, Transaction, TransactionType
from app.crud import create_fund, create_company, create_transaction
from app.logic.metrics import calculate_fund_metrics
from datetime import date
import os

# Use a local SQLite for testing if no DB_URL provided
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL)

def seed_data():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # 1. Create Fund
        fund = Fund(
            name="Hashiras: Yoriichi I",
            fund_code="YORIICHI-I",
            fund_start_date=date(2026, 4, 1),
            total_commitment=100000000,
            management_fee_pct=0.005,
            carry_pct=0.35
        )
        session.add(fund)
        session.commit()
        session.refresh(fund)
        print(f"Created Fund: {fund.name} ({fund.id})")

        # 2. Create Companies (A-E)
        companies = []
        for name in ["Company A", "Company B", "Company C", "Company D", "Company E"]:
            company = PortfolioCompany(
                fund_id=fund.id,
                name=name,
                initial_investment_amount=1250000,
                initial_investment_date=date(2026, 4, 1),
                follow_on_reserved_amount=17000000,
                total_invested=0, # Will be updated by transactions
                ownership_pct=0.025,
                latest_post_money=50000000
            )
            session.add(company)
            companies.append(company)
        
        # Companies (F-H)
        for name in ["Company F", "Company G", "Company H"]:
            company = PortfolioCompany(
                fund_id=fund.id,
                name=name,
                initial_investment_amount=1250000,
                initial_investment_date=date(2026, 4, 1),
                total_invested=0
            )
            session.add(company)
            companies.append(company)
        
        session.commit()

        # 3. Create Transactions
        # Initial Capital Calls
        for company in companies:
            create_transaction(session, {
                "fund_id": fund.id,
                "company_id": company.id,
                "transaction_date": date(2026, 4, 1),
                "amount": 1250000,
                "tx_type": TransactionType.capital_call,
                "reference": "Initial Investment"
            })

        # Follow-ons for A-E
        for company in companies[:5]:
            create_transaction(session, {
                "fund_id": fund.id,
                "company_id": company.id,
                "transaction_date": date(2027, 5, 1),
                "amount": 17000000,
                "tx_type": TransactionType.capital_call,
                "reference": "Follow-on"
            })

        # 4. Create Distributions (Exits)
        # Example: Company A exits for 182.5M
        create_transaction(session, {
            "fund_id": fund.id,
            "company_id": companies[0].id,
            "transaction_date": date(2032, 3, 12),
            "amount": 182500000,
            "tx_type": TransactionType.distribution,
            "reference": "Exit Sale - Company A"
        })

        # 5. Calculate Metrics
        metrics = calculate_fund_metrics(session, fund.id)
        print("\nFund Metrics:")
        for k, v in metrics.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    seed_data()
