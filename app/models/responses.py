from pydantic import BaseModel
from typing import Optional, Dict, List

class LoanChatResponse(BaseModel):
    session_id: str
    user_message: str

    assistant_message: str

    loan_offer: Optional[Dict] = None
    risk_summary: Dict
    compliance_status: str

    confidence_signals: Dict

    decision_explanation: str
    agent_trace: List[Dict]

    next_action: str
