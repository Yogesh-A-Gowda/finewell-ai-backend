from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.TransactionResponse)
def add_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.transaction_type not in ("credit", "debit"):
        raise HTTPException(status_code=400, detail="transaction_type must be 'credit' or 'debit'")

    if payload.transaction_type == "credit":
        new_balance = current_user.current_balance + payload.amount
    else:
        if payload.amount > current_user.current_balance:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        new_balance = current_user.current_balance - payload.amount

    txn = models.Transaction(
        user_id=current_user.id,
        amount=payload.amount,
        transaction_type=payload.transaction_type,
        category=payload.category,
        description=payload.description,
        upi_ref=payload.upi_ref,
        balance_after=new_balance,
        is_penalty=payload.is_penalty,
    )
    db.add(txn)

    current_user.current_balance = new_balance
    db.commit()
    db.refresh(txn)

    # Auto-generate low balance alert
    _check_and_create_alert(db, current_user)
    return txn


@router.get("/", response_model=List[schemas.TransactionResponse])
def list_transactions(
    limit: int = 50,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    )
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(models.Transaction.date >= since)
    return query.order_by(models.Transaction.date.desc()).limit(limit).all()


@router.delete("/{txn_id}")
def delete_transaction(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == txn_id,
        models.Transaction.user_id == current_user.id,
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Reverse the balance
    if txn.transaction_type == "credit":
        current_user.current_balance -= txn.amount
    else:
        current_user.current_balance += txn.amount

    db.delete(txn)
    db.commit()
    return {"message": "Transaction deleted"}


def _check_and_create_alert(db: Session, user: models.User):
    from app.services.prediction import calculate_penalty_risk
    from datetime import timedelta
    risk, reason = calculate_penalty_risk(user)
    if risk in ("High", "Medium"):
        cutoff = datetime.utcnow() - timedelta(hours=24)
        existing = (
            db.query(models.Alert)
            .filter(
                models.Alert.user_id == user.id,
                models.Alert.alert_type == "penalty_risk",
                models.Alert.created_at >= cutoff,  # any alert within 24h, read or not
            )
            .first()
        )
        if not existing:
            alert = models.Alert(
                user_id=user.id,
                alert_type="penalty_risk",
                severity=risk.lower(),
                title=f"Balance Alert - {risk} Risk",
                message=reason,
            )
            db.add(alert)
            db.commit()
