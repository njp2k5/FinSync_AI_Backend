# app/api/routes_dashboard.py
# app/api/routes_dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.domain_models import User, UserProfile, Offer
from app.services.jwt_service import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/{user_id}")
def dashboard(user_id: str, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # get latest profile if any (might be tied to last session)
    profile = db.exec(select(UserProfile).where(UserProfile.customer_id == user_id).order_by(UserProfile.created_at.desc())).first()
    loans = db.exec(select(Offer).where(Offer.user_id == user_id)).all()

    curated = [
        {"loan_type": "Car Loan", "amount": 300000, "interest": 12.5, "tenure": 36},
        {"loan_type": "Personal Loan", "amount": 150000, "interest": 14.5, "tenure": 18},
        {"loan_type": "Education Loan", "amount": 500000, "interest": 9.5, "tenure": 60},
    ]

    return {
        "greeting": f"Hi {user.name}",
        "credit_score": getattr(profile, "income_monthly", None),
        "sanctioned_loans": loans,
        "curated_offers": curated,
    }
