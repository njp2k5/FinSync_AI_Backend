# app/agents/verification_agent.py
from app.services.mock_data_service import get_customer
from typing import Dict, Any
from sqlmodel import Session
from uuid import UUID


def run_verification_agent(db: Session, session_id: UUID, customer_id: str) -> Dict[str, Any]:
    """Run a lightweight verification check for a customer.

    Signature is kept compatible with other agents which accept (db, session_id, ...)
    so callers can pass the same arguments. The db and session_id are available
    for potential future persistence or logging (currently unused).
    """
    # Keep db and session_id parameters to avoid breaking callers; use customer_id
    customer = get_customer(customer_id)

    if not customer:
        return {"verified": False, "reason": "Customer not found"}

    return {
        "verified": True,
        "phone": customer.get("phone"),
        "email": customer.get("email"),
        "pre_approved_limit": customer.get("pre_approved_limit"),
        "credit_score": customer.get("credit_score"),
    }

