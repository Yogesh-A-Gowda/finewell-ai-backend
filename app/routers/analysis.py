from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.prediction import get_transaction_stats, predict_cash_flow
from app.services.ai_service import analyze_financial_health

router = APIRouter()


@router.get("/health", response_model=schemas.FinancialHealthResponse)
def get_financial_health(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stats = get_transaction_stats(db, current_user.id, days=30)

    user_data = {
        "name": current_user.name,
        "account_type": current_user.account_type,
        "bank_name": current_user.bank_name,
        "current_balance": current_user.current_balance,
        "min_balance": current_user.minimum_balance,
        "monthly_income": current_user.monthly_income,
        **stats,
    }

    ai_result = analyze_financial_health(user_data)

    return schemas.FinancialHealthResponse(
        health_score=ai_result.get("health_score", 50),
        penalty_risk=ai_result.get("penalty_risk", "Medium"),
        risk_details=ai_result.get("risk_details", ""),
        recommendations=ai_result.get("recommendations", []),
        cash_flow_7days=ai_result.get("cash_flow_7days", 0),
        monthly_surplus=stats["monthly_surplus"],
        penalty_savings_potential=ai_result.get("penalty_savings_potential", 0),
        ai_summary=ai_result.get("ai_summary", ""),
    )


@router.get("/cashflow", response_model=List[Dict])
def get_cashflow_forecast(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return predict_cash_flow(db, current_user.id, days_ahead=days)


@router.get("/spending-breakdown")
def get_spending_breakdown(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    txns = (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.transaction_type == "debit",
            models.Transaction.date >= since,
        )
        .all()
    )

    breakdown: dict = {}
    for t in txns:
        breakdown[t.category] = breakdown.get(t.category, 0) + t.amount

    total = sum(breakdown.values()) or 1
    return [
        {"category": cat, "amount": round(amt, 2), "percentage": round(amt / total * 100, 1)}
        for cat, amt in sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stats_30 = get_transaction_stats(db, current_user.id, days=30)
    stats_7 = get_transaction_stats(db, current_user.id, days=7)
    unread_alerts = (
        db.query(models.Alert)
        .filter(models.Alert.user_id == current_user.id, models.Alert.is_read == False)
        .count()
    )

    buffer = current_user.current_balance - current_user.minimum_balance
    return {
        "current_balance": current_user.current_balance,
        "minimum_balance": current_user.minimum_balance,
        "balance_buffer": buffer,
        "balance_buffer_pct": round(buffer / max(current_user.minimum_balance, 1) * 100, 1),
        "monthly_income": stats_30["monthly_credits"],
        "monthly_expenses": stats_30["monthly_debits"],
        "monthly_surplus": stats_30["monthly_surplus"],
        "weekly_expenses": stats_7["monthly_debits"],
        "total_penalties_30d": stats_30["total_penalties"],
        "unread_alerts": unread_alerts,
        "transaction_count_30d": stats_30["transaction_count"],
    }
