# app/api/routes_user.py
# app/api/routes_user.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.models.domain_models import User, UserProfile, Offer
from app.schemas.user_schemas import SaveProfileIn
from app.services.jwt_service import get_current_user
from app.api.routes_mocks import get_crm, get_credit, get_offer as mock_offer

router = APIRouter(prefix="/user", tags=["user"])

@router.post("/{user_id}/fetch-kyc")
def fetch_kyc(user_id: str, db: Session = Depends(get_session)):
    """
    Fetch CRM KYC mock and store as a UserProfile tied to a new SimulationSession or existing session.
    Note: original code used a separate KYC table — here we write into UserProfile for compatibility.
    """
    crm_data = get_crm(user_id)
    if not crm_data:
        raise HTTPException(status_code=404, detail="CRM data not found")

    # Create a UserProfile (you might want to tie it to a session later)
    profile = UserProfile(
        session_id=crm_data.get("session_id") or uuid.uuid4(),  # if crm doesn't provide session, create a placeholder
        customer_id=crm_data.get("customer_id"),
        name=crm_data.get("name", ""),
        age=crm_data.get("age", 0),
        income_monthly=crm_data.get("income_monthly", 0.0),
        existing_emi=crm_data.get("existing_emi", 0.0),
        employment_type=crm_data.get("employment_type", ""),
        loan_type=crm_data.get("loan_type", "Personal"),
        desired_amount=crm_data.get("desired_amount", 0.0),
        desired_tenure_months=crm_data.get("desired_tenure_months", 12)
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"saved": True, "profile": profile}

@router.post("/{user_id}/fetch-credit-score")
def fetch_credit(user_id: str):
    return get_credit(user_id)

@router.post("/{user_id}/fetch-offers")
def fetch_offers(user_id: str):
    return mock_offer(user_id)

@router.post("/{user_id}/save-profile")
def save_profile(user_id: str, payload: SaveProfileIn, db: Session = Depends(get_session)):
    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # update basic profile fields on User (phone as example)
    user.phone = payload.phone
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"saved": True, "user": user}

@router.get("/{user_id}/loans")
def get_loans(user_id: str, db: Session = Depends(get_session)):
    loans = db.exec(select(Offer).where(Offer.user_id == user_id)).all()
    return {"loans": loans}
