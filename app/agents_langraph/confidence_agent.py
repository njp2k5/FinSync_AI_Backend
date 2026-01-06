from app.graph.state import LoanGraphState

def confidence_agent(state: LoanGraphState) -> LoanGraphState:
    msg = state["user_message"]

    signals = {
        "hesitation": "?" in msg,
        "clarification_count": msg.count("?"),
        "response_latency": "mocked"
    }

    state["confidence_output"] = signals
    state["agent_trace"].append({
        "agent": "ConfidenceAgent",
        "decision": "Detected conversational friction",
        "details": signals
    })

    return state
