from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.domain_models import User, UserProfile, Offer
from app.services.jwt_service import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """
    Returns dashboard data for the authenticated user only
    """

    # Shared BFSI / CRM identifier
    customer_id = current_user.customer_id

    # Latest profile (if exists)
    profile = (
        db.exec(
            select(UserProfile)
            .where(UserProfile.customer_id == customer_id)
            .order_by(UserProfile.created_at.desc())
        )
        .first()
    )

    # All sanctioned offers for this customer
    sanctioned_loans = (
        db.exec(
            select(Offer)
            .where(Offer.session_id.isnot(None))
        )
        .all()
    )

    # Static curated offers (frontend-friendly)
    curated_offers = [
        {
            "loan_type": "Car Loan",
            "amount": 300000,
            "interest_rate": 12.5,
            "tenure_months": 36,
        },
        {
            "loan_type": "Personal Loan",
            "amount": 150000,
            "interest_rate": 14.5,
            "tenure_months": 18,
        },
        {
            "loan_type": "Education Loan",
            "amount": 500000,
            "interest_rate": 9.5,
            "tenure_months": 60,
        },
    ]

    return {
        "greeting": f"Hi {current_user.name}",
        "customer_id": customer_id,
        "profile_summary": {
            "income_monthly": getattr(profile, "income_monthly", None),
            "existing_emi": getattr(profile, "existing_emi", None),
            "loan_type": getattr(profile, "loan_type", None),
        },
        "sanctioned_loans": sanctioned_loans,
        "curated_offers": curated_offers,
    }
