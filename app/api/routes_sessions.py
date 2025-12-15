# app/api/routes_sessions.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from uuid import UUID
from pathlib import Path
import shutil, uuid as _uuid, os
from typing import Optional
from pydantic import BaseModel

from app.core.db import get_session
from app.schemas.session_schemas import (
    UserProfileCreate, SessionStartResponse, ChatMessageIn, ChatResponse
)
from app.models.domain_models import (
    SimulationSession, UserProfile, Message, Offer, AgentLog, SessionStatus, OfferStatus
)
from app.services.chat_service import handle_user_message, resume_underwriting_after_salary
from app.services.pdf_service import generate_sanction_pdf
from app.services.pdf_mailer import augment_pdf_with_pypdf, send_email_smtp

router = APIRouter(prefix="/sessions", tags=["sessions"])

UPLOAD_ROOT = Path("uploads")
UPLOAD_ROOT.mkdir(exist_ok=True)

class SessionStartIn(BaseModel):
    customer_id: Optional[str] = None


@router.post("/start", response_model=SessionStartResponse)
def create_session(body: Optional[SessionStartIn] = None, customer_id: Optional[str] = None, db: Session = Depends(get_session)):
    """Start a new session. Accepts an optional `customer_id` query param.

    NOTE: The endpoint previously accepted a `session_id` query param which caused
    validation issues when a non-UUID value was passed. To avoid ambiguity the
    endpoint now accepts `customer_id` (string) and always returns a server-
    generated `session_id`.
    """
    # create a new session (always server-generated id)
    session = SimulationSession(status=SessionStatus.IN_PROGRESS)
    # prefer explicit query param, then body
    customer = customer_id or (body.customer_id if body else None)
    if customer:
        session.customer_id = customer
    db.add(session); db.commit(); db.refresh(session)

    # Create a placeholder UserProfile so other endpoints relying on its presence work.
    # Use safe defaults; the profile can be updated later through conversation or admin APIs.
    placeholder = UserProfile(
        session_id=session.id,
        customer_id=customer,
        name="Unknown",
        age=0,
        income_monthly=0.0,
        existing_emi=0.0,
        employment_type="unknown",
        loan_type="unknown",
        desired_amount=0.0,
        desired_tenure_months=0,
    )
    db.add(placeholder); db.commit(); db.refresh(placeholder)

    return SessionStartResponse(session_id=session.id, status=session.status, customer_id=customer)

@router.post("/{session_id}/message", response_model=ChatResponse)
def post_message(session_id: UUID, message: ChatMessageIn, db: Session = Depends(get_session)):
    # Delegates completely to chat_service to handle the logic and google api call
    return handle_user_message(db=db, session_id=session_id, message=message)

@router.get("/{session_id}")
def get_session_summary(session_id: UUID, db: Session = Depends(get_session)):
    sess = db.get(SimulationSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    user = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    offer = db.exec(select(Offer).where(Offer.session_id == session_id)).first()
    return {"session": sess, "user_profile": user, "latest_offer": offer}

@router.get("/{session_id}/messages")
def get_messages(session_id: UUID, db: Session = Depends(get_session)):
    msgs = db.exec(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
    return {"messages": msgs}

@router.post("/{session_id}/upload-salary")
def upload_salary(
    session_id: UUID,
    file: UploadFile = File(...),
    declared_salary: Optional[float] = Form(None),
    db: Session = Depends(get_session)
):
    sess = db.get(SimulationSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    dest_dir = UPLOAD_ROOT / str(session_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"salary_{_uuid.uuid4().hex}_{file.filename}"
    
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # If declared_salary provided, store in profile
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    if declared_salary:
        profile.salary_reported = declared_salary
        db.add(profile); db.commit(); db.refresh(profile)

    # resume underwriting flow
    result = resume_underwriting_after_salary(db=db, session_id=session_id, salary_slip_path=str(dest_path))
    return result

@router.get("/{session_id}/uploads/{filename}")
def serve_upload(session_id: UUID, filename: str):
    path = UPLOAD_ROOT / str(session_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path), media_type="application/octet-stream", filename=filename)

@router.get("/{session_id}/sanction-letter")
def get_sanction_letter(session_id: UUID, db: Session = Depends(get_session)):
    offer = db.exec(select(Offer).where(Offer.session_id == session_id)).first()
    if not offer or offer.status != OfferStatus.APPROVED:
        raise HTTPException(status_code=404, detail="No approved offer / sanction letter available")
    
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    
    # Get last agent log or empty dict if none exists
    agent_log_entry = db.exec(select(AgentLog).where(AgentLog.session_id == session_id).order_by(AgentLog.created_at.desc())).first()
    log_data = agent_log_entry.log if agent_log_entry else {}

    # create pdf on demand
    reference_id = str(_uuid.uuid4())[:8]
    out_dir = UPLOAD_ROOT / str(session_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(out_dir / f"sanction_{reference_id}.pdf")
    
    generate_sanction_pdf(pdf_path, profile.name, {
        "amount": offer.amount,
        "tenure_months": offer.tenure_months,
        "interest_rate": offer.interest_rate,
        "monthly_emi": offer.monthly_emi,
        "status": offer.status,
        "reason_summary": offer.reason_summary
    }, log_data, reference_id)
    
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"sanction_{reference_id}.pdf")

@router.post("/{session_id}/finalize")
def finalize_session(session_id: UUID, approved: bool = Form(...), db: Session = Depends(get_session)):
    sess = db.get(SimulationSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
        
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    
    if approved:
        # produce an offer record if not present
        existing_offer = db.exec(select(Offer).where(Offer.session_id == session_id)).first()
        if not existing_offer:
            offer = Offer(
                session_id=session_id,
                requested_amount=profile.desired_amount,
                amount=profile.desired_amount,
                tenure_months=profile.desired_tenure_months,
                interest_rate=13.5,
                monthly_emi=0,
                status=OfferStatus.APPROVED,
                reason_summary="Manually finalized"
            )
            db.add(offer); db.commit(); db.refresh(offer)
            # only set latest_offer_id if model has the field (backwards-compatible)
            if hasattr(sess, "latest_offer_id"):
                sess.latest_offer_id = offer.id
            
        sess.status = SessionStatus.COMPLETED
        db.add(sess); db.commit()
        
        # generate PDF
        out_dir = UPLOAD_ROOT / str(session_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        reference_id = str(_uuid.uuid4())[:8]
        pdf_path = str(out_dir / f"sanction_{reference_id}.pdf")
        
        generate_sanction_pdf(pdf_path, profile.name, {
            "amount": profile.desired_amount,
            "tenure_months": profile.desired_tenure_months,
            "interest_rate": 13.5,
            "monthly_emi": 0,
            "status": OfferStatus.APPROVED,
            "reason_summary": "Finalized by admin"
        }, {}, reference_id)
        
        try:
            augment_pdf_with_pypdf(pdf_path, {"ref": reference_id, "customer": profile.name})
        except Exception:
            pass
            
        email_status = None
        if getattr(profile, "email", None):
            try:
                send_email_smtp(
                    smtp_config={
                        "host": os.getenv("SMTP_HOST"),
                        "port": int(os.getenv("SMTP_PORT") or 587),
                        "user": os.getenv("SMTP_USER"),
                        "password": os.getenv("SMTP_PASS"),
                        "sender": os.getenv("SENDER_EMAIL")
                    },
                    to_email=profile.email,
                    subject=f"Sanction Letter [{reference_id}]",
                    body=f"Dear {profile.name},\nPlease find attached sanction letter.\nRef: {reference_id}",
                    attachments=[pdf_path]
                )
                email_status = "sent"
            except Exception as e:
                email_status = f"error: {e}"
                
        return {"message": "finalized", "pdf_path": pdf_path, "email_status": email_status}
    else:
        sess.status = SessionStatus.REJECTED
        db.add(sess); db.commit()
        return {"message": "session marked rejected"}