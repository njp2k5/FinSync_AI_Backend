from typing import TypedDict, Dict, List, Optional

class LoanGraphState(TypedDict):
    session_id: str
    user_message: str

    financial_profile: Dict

    sales_output: Optional[Dict]
    risk_output: Optional[Dict]
    compliance_output: Optional[Dict]
    confidence_output: Optional[Dict]

    agent_trace: List[Dict]
    decision_log: List[str]

    assistant_message: Optional[str]
    next_action: Optional[str]
