from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.prediction import generate_smart_alerts

router = APIRouter()


def _maybe_insert_alerts(db: Session, current_user: models.User):
    """Insert a smart alert only if no alert of the same type was created in the last 24 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    new_alerts = generate_smart_alerts(db, current_user)
    for a in new_alerts:
        existing = (
            db.query(models.Alert)
            .filter(
                models.Alert.user_id == current_user.id,
                models.Alert.alert_type == a["alert_type"],
                models.Alert.created_at >= cutoff,   # read OR unread — within 24h
            )
            .first()
        )
        if not existing:
            db.add(models.Alert(user_id=current_user.id, **a))
    db.commit()


@router.get("/", response_model=List[schemas.AlertResponse])
def list_alerts(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _maybe_insert_alerts(db, current_user)

    query = db.query(models.Alert).filter(models.Alert.user_id == current_user.id)
    if unread_only:
        query = query.filter(models.Alert.is_read == False)
    return query.order_by(models.Alert.created_at.desc()).limit(50).all()


@router.put("/{alert_id}/read")
def mark_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    alert = db.query(models.Alert).filter(
        models.Alert.id == alert_id,
        models.Alert.user_id == current_user.id,
    ).first()
    if alert:
        alert.is_read = True
        db.commit()
    return {"message": "marked read"}


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.query(models.Alert).filter(
        models.Alert.user_id == current_user.id,
        models.Alert.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "all alerts marked read"}
