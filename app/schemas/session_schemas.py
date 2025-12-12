# app/schemas/session_schemas.py
# app/schemas/session_schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from app.models.domain_models import OfferStatus, SessionStatus

class UserProfileCreate(BaseModel):
    customer_id: Optional[str] = None
    name: str
    age: int
    income_monthly: float
    existing_emi: float
    employment_type: str
    loan_type: str
    desired_amount: float
    desired_tenure_months: int
    mood: Optional[str] = None
    email: Optional[str] = None

class OfferOut(BaseModel):
    requested_amount: float
    amount: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    status: OfferStatus
    reason_summary: str
    pre_approved_limit: Optional[float] = None
    decision_reason: Optional[str] = None

class SessionStartResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    user_profile: UserProfileCreate

class ChatMessageIn(BaseModel):
    sender: str
    text: str
    mood_override: Optional[str] = None

class ChatReply(BaseModel):
    text: str
    is_final_offer: bool = False
    final_offer: Optional[OfferOut] = None
    next_action: Optional[str] = None

class InternalLogOut(BaseModel):
    emotion_agent: Dict[str, Any]
    sales_agent: Dict[str, Any]
    verification_agent: Dict[str, Any]
    underwriting_agent: Dict[str, Any]
    agent_lines: Optional[List[str]] = None
    model_response: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    session_id: UUID
    reply: ChatReply
    internal_log: Optional[InternalLogOut] = None
