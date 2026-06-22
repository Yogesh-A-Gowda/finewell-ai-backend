from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app import models
import numpy as np


CATEGORIES = [
    "food", "transport", "utilities", "rent", "emi",
    "shopping", "medical", "education", "entertainment", "other",
]

PENALTY_AMOUNTS = {
    "savings": 600,
    "current": 1200,
    "jan_dhan": 0,
    "salary": 0,
}


def get_transaction_stats(db: Session, user_id: int, days: int = 30) -> Dict:
    since = datetime.utcnow() - timedelta(days=days)
    txns = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id, models.Transaction.date >= since)
        .order_by(models.Transaction.date.desc())
        .all()
    )

    credits = sum(t.amount for t in txns if t.transaction_type == "credit")
    debits = sum(t.amount for t in txns if t.transaction_type == "debit")
    penalties = sum(t.amount for t in txns if t.is_penalty)

    category_totals: Dict[str, float] = {}
    for t in txns:
        if t.transaction_type == "debit":
            category_totals[t.category] = category_totals.get(t.category, 0) + t.amount

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "monthly_credits": credits,
        "monthly_debits": debits,
        "monthly_surplus": credits - debits,
        "total_penalties": penalties,
        "top_categories": [f"{cat}: ₹{amt:,.0f}" for cat, amt in top_categories],
        "recent_summary": (
            f"{len(txns)} transactions: ₹{credits:,.0f} in, ₹{debits:,.0f} out"
        ),
        "transaction_count": len(txns),
    }


def predict_cash_flow(db: Session, user_id: int, days_ahead: int = 7) -> List[Dict]:
    """Simple rolling-average cash flow forecast."""
    since = datetime.utcnow() - timedelta(days=60)
    txns = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id, models.Transaction.date >= since)
        .order_by(models.Transaction.date)
        .all()
    )

    if not txns:
        return []

    # Daily net amounts
    daily: Dict[str, float] = {}
    for t in txns:
        day = t.date.strftime("%Y-%m-%d")
        delta = t.amount if t.transaction_type == "credit" else -t.amount
        daily[day] = daily.get(day, 0) + delta

    values = list(daily.values())
    avg_daily = float(np.mean(values)) if values else 0
    std_daily = float(np.std(values)) if len(values) > 1 else abs(avg_daily * 0.2)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    current_balance = user.current_balance if user else 0

    forecast = []
    running_balance = current_balance
    for i in range(1, days_ahead + 1):
        day = datetime.utcnow() + timedelta(days=i)
        predicted_net = avg_daily
        running_balance += predicted_net
        forecast.append({
            "date": day.strftime("%Y-%m-%d"),
            "predicted_net": round(predicted_net, 2),
            "predicted_balance": round(running_balance, 2),
            "confidence_low": round(running_balance - std_daily, 2),
            "confidence_high": round(running_balance + std_daily, 2),
        })

    return forecast


def calculate_penalty_risk(user: models.User) -> Tuple[str, str]:
    """Returns (risk_level, reason) based on balance vs minimum."""
    if user.account_type in ("jan_dhan", "salary"):
        return "Low", "Your account type (Jan Dhan/Salary) has zero minimum balance requirement."

    buffer = user.current_balance - user.minimum_balance
    buffer_pct = (buffer / max(user.minimum_balance, 1)) * 100

    if buffer < 0:
        return "High", f"Balance is ₹{abs(buffer):,.0f} BELOW minimum. Penalty may already apply."
    elif buffer_pct < 20:
        return "High", f"Only ₹{buffer:,.0f} above minimum ({buffer_pct:.0f}% buffer). Very risky."
    elif buffer_pct < 50:
        return "Medium", f"₹{buffer:,.0f} above minimum ({buffer_pct:.0f}% buffer). Keep monitoring."
    else:
        return "Low", f"₹{buffer:,.0f} above minimum ({buffer_pct:.0f}% buffer). Looking good."


def generate_smart_alerts(db: Session, user: models.User) -> List[Dict]:
    """Generate rule-based alerts for the user."""
    alerts = []
    risk_level, risk_reason = calculate_penalty_risk(user)

    if risk_level == "High":
        alerts.append({
            "alert_type": "penalty_risk",
            "severity": "high",
            "title": "Penalty Risk: Critical",
            "message": risk_reason,
        })
    elif risk_level == "Medium":
        alerts.append({
            "alert_type": "low_balance",
            "severity": "medium",
            "title": "Low Balance Warning",
            "message": risk_reason,
        })

    stats = get_transaction_stats(db, user.id, days=30)
    if stats["monthly_surplus"] < 0:
        alerts.append({
            "alert_type": "cash_flow",
            "severity": "high",
            "title": "Spending Exceeds Income",
            "message": (
                f"You spent ₹{abs(stats['monthly_surplus']):,.0f} more than you earned this month. "
                "Review your expenses immediately."
            ),
        })
    elif stats["monthly_surplus"] < user.monthly_income * 0.1:
        alerts.append({
            "alert_type": "cash_flow",
            "severity": "medium",
            "title": "Low Monthly Savings",
            "message": (
                f"Monthly surplus is only ₹{stats['monthly_surplus']:,.0f}. "
                "Aim to save at least 20% of income."
            ),
        })

    return alerts
