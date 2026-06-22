from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = ""
    password: str
    account_type: str = "savings"
    minimum_balance: float = 1000.0
    current_balance: float = 0.0
    monthly_income: float = 0.0
    bank_name: str = ""


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    account_type: str
    minimum_balance: float
    current_balance: float
    monthly_income: float
    bank_name: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    account_type: Optional[str] = None
    minimum_balance: Optional[float] = None
    current_balance: Optional[float] = None
    monthly_income: Optional[float] = None
    bank_name: Optional[str] = None


# ── Transactions ──────────────────────────────────────────────────────────────
class TransactionCreate(BaseModel):
    amount: float
    transaction_type: str  # credit | debit
    category: str = "other"
    description: str = ""
    upi_ref: str = ""
    is_penalty: bool = False


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    transaction_type: str
    category: str
    description: str
    upi_ref: str
    balance_after: float
    date: datetime
    is_penalty: bool

    class Config:
        from_attributes = True


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertResponse(BaseModel):
    id: int
    user_id: int
    alert_type: str
    severity: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []


# ── Analysis ─────────────────────────────────────────────────────────────────
class FinancialHealthResponse(BaseModel):
    health_score: int
    penalty_risk: str
    risk_details: str
    recommendations: List[str]
    cash_flow_7days: float
    monthly_surplus: float
    penalty_savings_potential: float
    ai_summary: str
