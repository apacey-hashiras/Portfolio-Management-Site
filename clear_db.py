from sqlmodel import Session, create_engine, select, delete
from app.models import Fund, PortfolioCompany, Transaction, WaterfallAllocation
from app.config import settings
import os

def clear_database():
    # Use the pooler URL from environment if available, else from settings
    database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    engine = create_engine(database_url)
    
    with Session(engine) as session:
        print("Clearing database...")
        
        # Delete in order of dependencies
        session.exec(delete(WaterfallAllocation))
        session.exec(delete(Transaction))
        session.exec(delete(PortfolioCompany))
        session.exec(delete(Fund))
        
        session.commit()
        print("Database cleared successfully! You can now start adding your own data.")

if __name__ == "__main__":
    clear_database()
