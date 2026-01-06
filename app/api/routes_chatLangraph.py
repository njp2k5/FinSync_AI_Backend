from fastapi import APIRouter, HTTPException
from app.core.session import SessionStore
from app.graph.runtime import run_loan_graph
from app.models.responses import LoanChatResponse
import uuid

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/start")
def start_chat():
    session_id = str(uuid.uuid4())

    SessionStore.create_session(
        session_id=session_id,
        financial_profile={
            "income": 50000,          # placeholder
            "credit_score": 720,      # placeholder
            "obligations": 10000
        }
    )

    return {"session_id": session_id}


@router.post("/message", response_model=LoanChatResponse)
def chat_message(session_id: str, user_message: str):
    session = SessionStore.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session")

    final_state = run_loan_graph(
        session_id=session_id,
        user_message=user_message,
        financial_profile=session["financial_profile"]
    )

    return LoanChatResponse(
        session_id=session_id,
        user_message=user_message,
        assistant_message=final_state["assistant_message"],
        loan_offer=final_state.get("sales_output"),
        risk_summary=final_state["risk_output"],
        compliance_status=final_state["compliance_output"]["status"],
        confidence_signals=final_state["confidence_output"],
        decision_explanation=" | ".join(final_state["decision_log"]),
        agent_trace=final_state["agent_trace"],
        next_action=final_state["next_action"]
    )


@router.get("/decision")
def decision_summary(session_id: str):
    session = SessionStore.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Invalid session")

    return {
        "session_id": session_id,
        "note": "Decision details are returned via /chat/message for auditability"
    }
