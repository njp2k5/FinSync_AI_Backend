from sqlmodel import Session, select
from app.models.domain_models import UserProfile
import math

def calculate_emi(amount, rate, tenure_months):
    tenure_years = tenure_months / 12
    return (amount * (1 + (rate / 100) * tenure_years)) / tenure_months

def run_risk_agent(db: Session, session_id, sales_result: dict):
    profile = db.exec(
        select(UserProfile).where(UserProfile.session_id == session_id)
    ).first()

    proposed_amount = sales_result["proposed_amount"]
    tenure = sales_result["tenure_months"]
    rate = sales_result["interest_rate"]

    emi = calculate_emi(proposed_amount, rate, tenure)
    total_emi = emi + profile.existing_emi
    emi_ratio = total_emi / profile.income_monthly

    adjusted_amount = proposed_amount
    adjusted_rate = rate
    comment = "Risk within acceptable limits."

    # 🔴 Core Risk Rule
    if emi_ratio > 0.5:
        adjusted_amount = math.floor(proposed_amount * 0.8)  # reduce by 20%
        emi = calculate_emi(adjusted_amount, rate, tenure)
        comment = "EMI exceeded 50% of income. Amount reduced for safety."

    return {
        "adjusted_amount": adjusted_amount,
        "tenure_months": tenure,
        "interest_rate": adjusted_rate,
        "monthly_emi": round(emi, 2),
        "comment": comment
    }
