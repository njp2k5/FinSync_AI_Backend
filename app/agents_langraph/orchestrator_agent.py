from app.graph.state import LoanGraphState

def orchestrator_agent(state: LoanGraphState) -> LoanGraphState:
    compliance = state["compliance_output"]

    if compliance["status"] == "REJECTED":
        state["assistant_message"] = (
            "We cannot proceed due to policy constraints. "
            "Would you like to explore alternative options?"
        )
        state["next_action"] = "reject"
    else:
        state["assistant_message"] = (
            "Based on your profile, here is a compliant loan offer for your review."
        )
        state["next_action"] = "present_offer"

    state["decision_log"].append("Final decision consolidated by Orchestrator")

    state["agent_trace"].append({
        "agent": "OrchestratorAgent",
        "decision": "Produced final customer-facing outcome",
        "details": state["next_action"]
    })

    return state
