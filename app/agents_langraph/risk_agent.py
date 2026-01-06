from app.graph.state import LoanGraphState

def risk_agent(state: LoanGraphState) -> LoanGraphState:
    profile = state["financial_profile"]

    emi_capacity = profile["income"] * 0.4
    assumed_emi = 15000  # mocked

    risk_flags = []
    if assumed_emi > emi_capacity:
        risk_flags.append("EMI exceeds affordability")

    output = {
        "emi_capacity": emi_capacity,
        "risk_flags": risk_flags,
        "max_safe_amount": profile["income"] * 8
    }

    state["risk_output"] = output
    state["agent_trace"].append({
        "agent": "RiskAgent",
        "decision": "Assessed affordability and exposure",
        "details": output
    })

    return state
