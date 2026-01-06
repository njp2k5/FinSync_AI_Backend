# app/agents/sales_agent.py
from sqlmodel import Session, select
from app.models.domain_models import UserProfile

def run_sales_agent(db: Session, session_id, requested_amount: float, tenure_months: int):
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        return {"proposed_amount": requested_amount, "tenure_months": tenure_months, "interest_rate": 13.5, "comment": "profile missing"}
    base_rate = 13.5
    if profile.loan_type.lower() == "education loan":
        base_rate = 10.5
    elif profile.loan_type.lower() == "msme loan":
        base_rate = 15.5
    return {
        "proposed_amount": requested_amount,
        "tenure_months": tenure_months,
        "interest_rate": base_rate,
        "comment": "Sales proposes requested amount"
    }
