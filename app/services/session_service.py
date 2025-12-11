from sqlmodel import Session
from uuid import uuid4
from datetime import datetime
from app.models.domain_models import SimulationSession, UserProfile, SessionStatus
from app.schemas.session_schemas import UserProfileCreate, SessionStartResponse

def start_session(db: Session, profile: UserProfileCreate) -> SessionStartResponse:
    # create session
    session = SimulationSession(status=SessionStatus.PENDING)
    db.add(session)
    db.commit()
    db.refresh(session)

    # create profile
    user_profile = UserProfile(
        session_id=session.id,
        **profile.dict()
    )
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)

    session.status = SessionStatus.IN_PROGRESS
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)

    return SessionStartResponse(
        session_id=session.id,
        status=session.status,
        user_profile=profile
    )
