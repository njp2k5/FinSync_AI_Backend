# app/api/routes_sessions.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select
from uuid import UUID
from pathlib import Path
import shutil
import uuid as _uuid

from app.core.db import get_session
from app.schemas.session_schemas import (
    UserProfileCreate, SessionStartResponse, ChatMessageIn, ChatResponse, ChatReply
)
from app.models.domain_models import SimulationSession, UserProfile, Message, Offer, AgentLog, SessionStatus, OfferStatus
from app.services.chat_service import handle_user_message, resume_underwriting_after_salary
from app.services.pdf_service import generate_sanction_pdf

router = APIRouter(prefix="/sessions", tags=["sessions"])

UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(exist_ok=True)

@router.post("/start", response_model=SessionStartResponse)
def create_session(profile: UserProfileCreate, db: Session = Depends(get_session)):
    # Create session and profile
    session = SimulationSession(status=SessionStatus.IN_PROGRESS)
    db.add(session)
    db.commit()
    db.refresh(session)

    user_profile = UserProfile(session_id=session.id, **profile.dict())
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)

    # Save session.customer_id if provided
    if profile.customer_id:
        session.customer_id = profile.customer_id
        db.add(session)
        db.commit()
        db.refresh(session)

    return SessionStartResponse(session_id=session.id, status=session.status, user_profile=profile)

@router.post("/{session_id}/message", response_model=ChatResponse)
def post_message(session_id: UUID, message: ChatMessageIn, db: Session = Depends(get_session)):
    # main orchestrator route
    return handle_user_message(db=db, session_id=session_id, message=message)

@router.post("/{session_id}/upload-salary")
def upload_salary(session_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_session)):
    sess = db.get(SimulationSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # save file under uploads/{session_id}/
    dest_dir = UPLOAD_ROOT / str(session_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"salary_{_uuid.uuid4().hex}_{file.filename}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # persist path to userprofile or offer (we will attach to latest offer)
    # For simplicity, set to the UserProfile.salary_reported if client provided declared salary in filename or metadata
    # Here we simply attach path, and resume underwriting
    result = resume_underwriting_after_salary(db=db, session_id=session_id, salary_slip_path=str(dest_path))

    return result

@router.get("/{session_id}/sanction-letter")
def get_sanction_letter(session_id: UUID, db: Session = Depends(get_session)):
    # Fetch latest offer and check if approved and pdf exists
    offer = db.exec(select(Offer).where(Offer.session_id == session_id)).first()
    if not offer or offer.status != OfferStatus.APPROVED:
        raise HTTPException(status_code=404, detail="No approved offer / sanction letter available")
    # expecting file path in offer.salary_slip_path or a stored path; we generate PDF on demand
    # For demo, generate PDF dynamically and return path
    agent_log = db.exec(select(AgentLog).where(AgentLog.session_id == session_id)).first()
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    reference_id = str(_uuid.uuid4())[:8]
    output_path = f"uploads/{session_id}/sanction_{reference_id}.pdf"
    generate_sanction_pdf(output_path, profile.name, {
        "amount": offer.amount,
        "tenure_months": offer.tenure_months,
        "interest_rate": offer.interest_rate,
        "monthly_emi": offer.monthly_emi,
        "status": offer.status,
        "reason_summary": offer.reason_summary
    }, agent_log.log if agent_log else {}, reference_id)
    return {"download_path": output_path}
