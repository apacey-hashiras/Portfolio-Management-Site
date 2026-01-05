from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List
from .database import engine, get_session, init_db
from .models import Fund, PortfolioCompany, Transaction, WaterfallAllocation
from .schemas import FundCreate, FundRead, PortfolioCompanyCreate, PortfolioCompanyRead, TransactionCreate, TransactionRead
from .api import funds, companies, transactions, metrics

app = FastAPI(title="Fund Portfolio Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()
    pass

@app.get("/")
def read_root():
    return {"message": "Welcome to the Fund Portfolio Management API"}

app.include_router(funds.router)
app.include_router(companies.router)
app.include_router(transactions.router)
app.include_router(metrics.router)
