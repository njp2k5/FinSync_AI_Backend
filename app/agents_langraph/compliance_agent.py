from app.graph.state import LoanGraphState

def compliance_agent(state: LoanGraphState) -> LoanGraphState:
    risk = state["risk_output"]

    status = "APPROVED_WITH_CONDITIONS"
    reasons = []

    if "EMI exceeds affordability" in risk["risk_flags"]:
        status = "REJECTED"
        reasons.append("Affordability policy breached")

    state["compliance_output"] = {
        "status": status,
        "reasons": reasons
    }

    state["agent_trace"].append({
        "agent": "ComplianceAgent",
        "decision": status,
        "details": reasons
    })

    return state
