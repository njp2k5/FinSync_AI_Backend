# app/models/domain_models.py
from sqlmodel import SQLModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy import Column
from sqlalchemy import JSON  # cross-db JSON

# --- NEW: persistent User account model (added without modifying any existing models) ---
class User(SQLModel, table=True):
    """
    Persistent user account for signup/login. Added so auth routes can reference a User.
    This does not replace UserProfile (which remains tied to SimulationSession).
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: str = Field(index=True, unique=True)
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    password_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Existing enums and models left unchanged ---

class SessionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    OFFER_GENERATED = "offer_generated"
    REJECTED = "rejected"
    COMPLETED = "completed"
    AWAITING_SALARY = "awaiting_salary"

class OfferStatus(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PENDING = "Pending"

class SimulationSession(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: SessionStatus = Field(default=SessionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    customer_id: Optional[str] = Field(default=None, index=True)  # ties to synthetic customers

class UserProfile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
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
    salary_reported: Optional[float] = None  # set after upload / parsing
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
    sender: str  # "user" | "bot"
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Offer(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
    requested_amount: float
    amount: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    status: OfferStatus
    reason_summary: str
    pre_approved_limit: Optional[float] = None
    decision_reason: Optional[str] = None
    salary_slip_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
    offer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="offer.id")

    # explicit JSON column so SQLModel knows how to store it
    log: Dict[str, Any] = Field(sa_column=Column(JSON), default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
