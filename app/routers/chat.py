from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.ai_service import chat_with_advisor

router = APIRouter()


@router.post("/", response_model=schemas.ChatResponse)
def chat(
    payload: schemas.ChatMessage,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_context = {
        "current_balance": current_user.current_balance,
        "min_balance": current_user.minimum_balance,
        "account_type": current_user.account_type,
        "monthly_income": current_user.monthly_income,
        "name": current_user.name,
    }
    result = chat_with_advisor(payload.message, user_context)
    return schemas.ChatResponse(
        response=result.get("response", "I'm unable to respond right now. Please try again."),
        suggestions=result.get("suggestions", []),
    )
