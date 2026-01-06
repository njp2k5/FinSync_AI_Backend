# app/agents/underwriting_agent.py
from math import floor
from typing import Optional

from app.services.mock_data_service import get_customer
from app.models.domain_models import OfferStatus


def calculate_emi(amount: float, rate: float, tenure_months: int) -> float:
    tenure_years = tenure_months / 12
    return (amount * (1 + (rate / 100) * tenure_years)) / tenure_months


def run_underwriting_agent(
    db,
    session_id,
    profile,
    sales_result,
    salary: Optional[float] = None,
):
    """
    Underwriting rules:
    - credit score < 700 → reject
    - amount <= pre-approved → affordability check
    - amount <= 2x pre-approved → require salary slip
    - amount > 2x pre-approved → reject
    """

    cust_id = profile.customer_id
    customer = get_customer(cust_id)

    if not customer:
        return {
            "approved": False,
            "reason": "customer_not_found",
            "pre_approved_limit": 0,
        }

    pre_approved = customer.get("pre_approved_limit", 0)
    credit_score = customer.get("credit_score", 600)

    requested_amount = profile.desired_amount
    tenure = sales_result["tenure_months"]
    rate = sales_result["interest_rate"]

    # 1️⃣ Credit score gate
    if credit_score < 700:
        return {
            "approved": False,
            "reason": "credit_score_too_low",
            "pre_approved_limit": pre_approved,
        }

    # 2️⃣ Within pre-approved limit
    if requested_amount <= pre_approved:
        emi = calculate_emi(requested_amount, rate, tenure)

        if profile.existing_emi + emi > 0.5 * profile.income_monthly:
            return {
                "approved": False,
                "reason": "affordability_failed",
                "pre_approved_limit": pre_approved,
            }

        return {
            "approved": True,
            "offer": {
                "amount": requested_amount,
                "tenure_months": tenure,
                "interest_rate": rate,
                "monthly_emi": round(emi, 2),
                "reason_summary": "Within pre-approved limit",
            },
            "pre_approved_limit": pre_approved,
        }

    # 3️⃣ Up to 2x pre-approved → salary required
    if requested_amount <= 2 * pre_approved:
        used_salary = salary or profile.salary_reported

        if not used_salary:
            return {
                "approved": None,
                "next_action": "require_salary_upload",
                "pre_approved_limit": pre_approved,
            }

        emi = calculate_emi(requested_amount, rate, tenure)

        if (
            emi <= 0.5 * used_salary
            and profile.existing_emi + emi <= 0.5 * used_salary
        ):
            return {
                "approved": True,
                "offer": {
                    "amount": requested_amount,
                    "tenure_months": tenure,
                    "interest_rate": rate,
                    "monthly_emi": round(emi, 2),
                    "reason_summary": "Approved after salary verification",
                },
                "pre_approved_limit": pre_approved,
            }

        return {
            "approved": False,
            "reason": "affordability_failed_after_salary",
            "pre_approved_limit": pre_approved,
        }

    # 4️⃣ Above 2x pre-approved → reject
    return {
        "approved": False,
        "reason": "exceeds_double_limit",
        "pre_approved_limit": pre_approved,
    }
