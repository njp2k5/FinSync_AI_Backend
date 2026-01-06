from app.graph.state import LoanGraphState

def sales_agent(state: LoanGraphState) -> LoanGraphState:
    profile = state["financial_profile"]

    offer = {
        "amount": min(500000, profile["income"] * 10),
        "tenure_months": 36,
        "interest_rate": 12.5
    }

    state["sales_output"] = offer
    state["agent_trace"].append({
        "agent": "SalesAgent",
        "decision": "Generated negotiable loan offer",
        "details": offer
    })

    return state
