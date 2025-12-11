# app/agents/underwriting_agent.py
from app.api.routes_mocks import CUSTOMERS
from app.services.utils import save_message
from app.models.domain_models import OfferStatus
from math import floor

def calculate_emi(amount, rate, tenure_months):
    tenure_years = tenure_months / 12
    return (amount * (1 + (rate / 100) * tenure_years)) / tenure_months

def run_underwriting_agent(db, session_id, profile, sales_result, salary: float = None):
    # Get pre-approved and credit score from mocks
    cust_id = profile.customer_id
    cust = CUSTOMERS.get(cust_id, {})
    pre_approved = cust.get("pre_approved_limit", 0)
    credit_score = cust.get("credit_score", 600)

    requested_amount = profile.desired_amount
    tenure = sales_result["tenure_months"]
    rate = sales_result["interest_rate"]

    # Reject for low credit score
    if credit_score < 700:
        return {"approved": False, "reason": "credit_score_too_low", "pre_approved_limit": pre_approved}

    # If within pre-approved limit -> simple affordability check
    if requested_amount <= pre_approved:
        emi = calculate_emi(requested_amount, rate, tenure)
        if profile.existing_emi + emi > 0.5 * profile.income_monthly:
            return {"approved": False, "reason": "affordability_failed", "pre_approved_limit": pre_approved}
        return {"approved": True, "offer": {
            "amount": requested_amount,
            "tenure_months": tenure,
            "interest_rate": rate,
            "monthly_emi": round(emi,2),
            "reason_summary": "Within pre-approved limit"
        }, "pre_approved_limit": pre_approved}

    # If <= 2x pre-approved -> require salary slip if not provided
    if requested_amount <= 2 * pre_approved:
        if salary is None and not profile.salary_reported:
            return {"approved": None, "next_action": "require_salary_upload", "pre_approved_limit": pre_approved}
        # use salary if provided (uploaded or reported)
        used_salary = salary if salary is not None else profile.salary_reported
        if used_salary is None:
            return {"approved": None, "next_action": "require_salary_upload", "pre_approved_limit": pre_approved}
        emi = calculate_emi(requested_amount, rate, tenure)
        # EMI must be <= 50% of salary AND total EMIs <= 50% salary as per spec
        if emi <= 0.5 * used_salary and profile.existing_emi + emi <= 0.5 * used_salary:
            return {"approved": True, "offer": {
                "amount": requested_amount,
                "tenure_months": tenure,
                "interest_rate": rate,
                "monthly_emi": round(emi,2),
                "reason_summary": "Approved after salary verification"
            }, "pre_approved_limit": pre_approved}
        return {"approved": False, "reason": "affordability_failed_after_salary", "pre_approved_limit": pre_approved}

    # Else > 2x pre-approved -> reject
    return {"approved": False, "reason": "exceeds_double_limit", "pre_approved_limit": pre_approved}
