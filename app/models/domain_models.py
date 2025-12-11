from sqlmodel import SQLModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy import Column
from sqlalchemy import JSON   # Cross-database JSON type (works for SQLite & Postgres)
from sqlalchemy.types import JSON as JSONType  # Type hint for JSON column

class SessionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    OFFER_GENERATED = "offer_generated"
    REJECTED = "rejected"
    COMPLETED = "completed"

class OfferStatus(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PENDING = "Pending"

class SimulationSession(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: SessionStatus = Field(default=SessionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    latest_offer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="offer.id")

class UserProfile(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
    name: str
    age: int
    income_monthly: float
    existing_emi: float
    employment_type: str
    loan_type: str
    desired_amount: float
    desired_tenure_months: int
    mood: Optional[str] = None
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
    amount: float
    tenure_months: int
    interest_rate: float
    monthly_emi: float
    status: OfferStatus
    reason_summary: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="simulationsession.id", index=True)
    offer_id: Optional[uuid.UUID] = Field(default=None, foreign_key="offer.id")

    # JSON column with explicit SQLAlchemy type
    log: Dict[str, Any] = Field(
        sa_column=Column(JSON),
        default_factory=dict
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
