# app/agents/verification_agent.py
from app.services.mock_data_service import get_customer

from typing import Dict

def run_verification_agent(customer_id: str):
    customer = get_customer(customer_id)

    if not customer:
        return {"verified": False, "reason": "Customer not found"}

    return {
        "verified": True,
        "phone": customer.get("phone"),
        "email": customer.get("email"),
    }

