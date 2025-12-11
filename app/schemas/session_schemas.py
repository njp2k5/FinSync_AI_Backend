from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.domain_models import OfferStatus, SessionStatus

class UserProfileCreate(BaseModel):
    name: str
    age: int
    income_monthly: float
    existing_emi: float
    employment_type: str
    loan_type: str
    desired_amount: float
    desired_tenure_months: int
    mood: Optional[str] = None

class OfferOut(BaseModel):
    amount: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    status: OfferStatus
    reason_summary: str

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

class InternalLogOut(BaseModel):
    emotion_agent: dict
    sales_agent: dict
    risk_agent: dict
    compliance_agent: dict

class ChatResponse(BaseModel):
    session_id: UUID
    reply: ChatReply
    internal_log: Optional[InternalLogOut] = None
    # you can add message history here if needed
