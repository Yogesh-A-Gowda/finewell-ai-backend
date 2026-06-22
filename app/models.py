from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class AccountType(str, enum.Enum):
    savings = "savings"
    current = "current"
    jan_dhan = "jan_dhan"
    salary = "salary"


class TransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class AlertSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class AlertType(str, enum.Enum):
    low_balance = "low_balance"
    penalty_risk = "penalty_risk"
    cash_flow = "cash_flow"
    recurring_expense = "recurring_expense"
    penalty_charged = "penalty_charged"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    hashed_password = Column(String, nullable=False)
    account_type = Column(String, default="savings")
    minimum_balance = Column(Float, default=1000.0)
    current_balance = Column(Float, default=0.0)
    monthly_income = Column(Float, default=0.0)
    bank_name = Column(String, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    transactions = relationship("Transaction", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    category = Column(String, default="other")
    description = Column(String, default="")
    upi_ref = Column(String, default="")
    balance_after = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    is_penalty = Column(Boolean, default=False)

    user = relationship("User", back_populates="transactions")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="alerts")
