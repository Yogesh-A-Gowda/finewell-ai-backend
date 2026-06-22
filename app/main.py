from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import users, transactions, analysis, alerts, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinWell AI",
    description="AI-Powered Financial Wellness Agent for India",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])


@app.get("/")
def root():
    return {
        "name": "FinWell AI",
        "description": "AI-Powered Financial Wellness Agent — Penalty Prevention for India",
        "status": "running",
        "docs": "/docs",
    }
