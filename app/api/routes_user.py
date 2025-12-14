from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.domain_models import (
    User,
    UserProfile,
    Offer,
    SimulationSession,
)
from app.schemas.user_schemas import SaveProfileIn
from app.services.jwt_service import get_current_user
from app.services.mock_data_service import get_customer

router = APIRouter(prefix="/user", tags=["user"])


# -------------------------
# Fetch & save KYC
# -------------------------
@router.post("/fetch-kyc")
def fetch_kyc(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    customer_id = current_user.customer_id

    customer = get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="CRM data not found")

    session = SimulationSession(customer_id=customer_id)
    db.add(session)
    db.commit()
    db.refresh(session)

    profile = UserProfile(
        session_id=session.id,
        customer_id=customer_id,
        name=customer.get("name", ""),
        age=customer.get("age", 0),
        income_monthly=customer.get("income_monthly", 0.0),
        existing_emi=customer.get("existing_emi", 0.0),
        employment_type=customer.get("employment_type", ""),
        loan_type="Personal",
        desired_amount=0.0,
        desired_tenure_months=12,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "saved": True,
        "session_id": str(session.id),
        "profile": profile,
    }


# -------------------------
# Credit score
# -------------------------
@router.post("/fetch-credit-score")
def fetch_credit_score(
    current_user: User = Depends(get_current_user),
):
    customer = get_customer(current_user.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"credit_score": customer.get("credit_score", 600)}


# -------------------------
# Pre-approved offers
# -------------------------
@router.post("/fetch-offers")
def fetch_offers(
    current_user: User = Depends(get_current_user),
):
    customer = get_customer(current_user.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"pre_approved_limit": customer.get("pre_approved_limit", 0)}


# -------------------------
# Save basic user profile
# -------------------------
@router.post("/save-profile")
def save_profile(
    payload: SaveProfileIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    current_user.phone = payload.phone
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {"saved": True, "user": current_user}


# -------------------------
# Loans
# -------------------------
@router.get("/loans")
def get_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    loans = db.exec(
        select(Offer)
        .join(SimulationSession)
        .where(SimulationSession.customer_id == current_user.customer_id)
    ).all()

    return {"loans": loans}
