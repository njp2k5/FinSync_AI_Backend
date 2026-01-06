from app.graph.builder import build_loan_graph

loan_graph = build_loan_graph()

def run_loan_graph(
    session_id: str,
    user_message: str,
    financial_profile: dict
):
    initial_state = {
        "session_id": session_id,
        "user_message": user_message,
        "financial_profile": financial_profile,

        "sales_output": None,
        "risk_output": None,
        "compliance_output": None,
        "confidence_output": None,

        "agent_trace": [],
        "decision_log": [],

        "assistant_message": None,
        "next_action": None
    }

    return loan_graph.invoke(initial_state)
