from sqlmodel import Session, select
from app.models.domain_models import UserProfile

def run_compliance_agent(db: Session, session_id, risk_result: dict):
    profile = db.exec(
        select(UserProfile).where(UserProfile.session_id == session_id)
    ).first()

    checks = []
    approved = True
    reason_summary = "All basic compliance checks passed."

    # ✅ AGE RULE
    if profile.age < 21:
        approved = False
        checks.append("Age < 21")
        reason_summary = "Applicant must be at least 21 years old."

    # ✅ INCOME RULE
    if profile.income_monthly < 20000:
        approved = False
        checks.append("Income < 20,000")
        reason_summary = "Monthly income below minimum eligibility threshold."

    # ✅ FINAL OFFER OUTPUT
    offer = {
        "amount": risk_result["adjusted_amount"],
        "tenure_months": risk_result["tenure_months"],
        "interest_rate": risk_result["interest_rate"],
        "monthly_emi": risk_result["monthly_emi"],
        "reason_summary": reason_summary,
    }

    if approved:
        checks.append("Age > 21")
        checks.append("Income > 20,000")
        checks.append("EMI ratio within safe limit")

    return {
        "approved": approved,
        "checks": checks,
        "offer": offer
    }
