# app/agents/verification_agent.py
from app.api.routes_mocks import CUSTOMERS
from typing import Dict

def run_verification_agent(db, session_id, customer_id) -> Dict:
    # For simplicity read from CUSTOMERS loaded earlier
    if not customer_id:
        return {"verification_passed": False, "issues": ["no_customer_id"]}
    cust = CUSTOMERS.get(customer_id)
    if not cust:
        return {"verification_passed": False, "issues": ["customer_not_found"]}
    issues = []
    if not cust.get("phone"):
        issues.append("missing_phone")
    if not cust.get("address"):
        issues.append("missing_address")
    return {"verification_passed": len(issues) == 0, "issues": issues, "crm_record": cust}
