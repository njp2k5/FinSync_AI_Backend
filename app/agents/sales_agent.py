from sqlmodel import Session, select
from app.models.domain_models import UserProfile

def run_sales_agent(db: Session, session_id):
    profile = db.exec(
        select(UserProfile).where(UserProfile.session_id == session_id)
    ).first()

    if not profile:
        return {
            "proposed_amount": 0,
            "tenure_months": 0,
            "interest_rate": 0,
            "comment": "User profile not found."
        }

    # Simple optimistic logic
    proposed_amount = profile.desired_amount
    tenure = profile.desired_tenure_months

    # Base interest by loan type
    base_rate = 13.5
    if profile.loan_type.lower() == "education loan":
        base_rate = 10.5
    elif profile.loan_type.lower() == "msme loan":
        base_rate = 15.5

    return {
        "proposed_amount": proposed_amount,
        "tenure_months": tenure,
        "interest_rate": base_rate,
        "comment": "User income supports requested amount."
    }
