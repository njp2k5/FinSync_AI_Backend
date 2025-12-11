# app/services/chat_service.py
from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException

from app.models.domain_models import (
    SimulationSession, Message, Offer, AgentLog, SessionStatus, OfferStatus, UserProfile
)
from app.agents.emotion_agent import run_emotion_agent
from app.agents.sales_agent import run_sales_agent
from app.agents.verification_agent import run_verification_agent
from app.agents.underwriting_agent import run_underwriting_agent
from app.services.utils import save_message


def handle_user_message(db: Session, session_id: UUID, message):
    # message is ChatMessageIn
    session = db.get(SimulationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save user message
    save_message(db, session_id, "user", message.text)

    # Load or create profile
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # 1. Emotion
    emotion_result = run_emotion_agent(message.text, mood_override=message.mood_override)

    # 2. Sales
    sales_result = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)

    # 3. Verification
    verification_result = run_verification_agent(db, session_id, profile.customer_id)

    # 4. Underwriting - calls mocks for pre-approved and credit score
    underwriting_result = run_underwriting_agent(db, session_id, profile, sales_result)

    # Build agent log
    log_payload = {
        "emotion_agent": emotion_result,
        "sales_agent": sales_result,
        "verification_agent": verification_result,
        "underwriting_agent": underwriting_result
    }

    # Persist AgentLog
    agent_log = AgentLog(session_id=session_id, log=log_payload)
    db.add(agent_log)
    db.commit()
    db.refresh(agent_log)

    # If underwriting requires salary upload:
    if underwriting_result.get("next_action") == "require_salary_upload":
        session.status = SessionStatus.AWAITING_SALARY
        db.add(session); db.commit()
        reply = ChatReply(text="We need a salary slip to proceed. Please upload your salary slip.", is_final_offer=False, next_action="require_salary_upload")
        return {
            "session_id": session_id,
            "reply": reply,
            "internal_log": log_payload
        }

    # If underwriting produced final offer:
    if underwriting_result.get("approved") is True:
        final_offer = underwriting_result["offer"]
        # Persist offer
        offer = Offer(
            session_id=session_id,
            requested_amount=profile.desired_amount,
            amount=final_offer["amount"],
            tenure_months=final_offer["tenure_months"],
            interest_rate=final_offer["interest_rate"],
            monthly_emi=final_offer["monthly_emi"],
            status=OfferStatus.APPROVED,
            reason_summary=final_offer.get("reason_summary", ""),
            pre_approved_limit=underwriting_result.get("pre_approved_limit")
        )
        db.add(offer); db.commit(); db.refresh(offer)
        session.latest_offer_id = offer.id
        session.status = SessionStatus.OFFER_GENERATED
        db.add(session); db.commit()
        reply = ChatReply(text="We have approved an offer. See details.", is_final_offer=True, final_offer=final_offer)
        save_message(db, session_id, "bot", reply.text)
        return {"session_id": session_id, "reply": reply, "internal_log": log_payload}

    # If underwriting rejected:
    reply = ChatReply(text=f"Sorry, we cannot approve this loan: {underwriting_result.get('reason')}", is_final_offer=True, final_offer=None)
    save_message(db, session_id, "bot", reply.text)
    session.status = SessionStatus.REJECTED
    db.add(session); db.commit()
    return {"session_id": session_id, "reply": reply, "internal_log": log_payload}

def resume_underwriting_after_salary(db: Session, session_id: UUID, salary_slip_path: str):
    # Attach salary slip path to profile and re-run underwriting
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    # For demo, assume filename contains salary or we set a fake salary; here we put a placeholder or parse later
    # Simple approach: use declared salary in filename like salary_50000.pdf -> parse 50000
    filename = salary_slip_path.split("_")
    declared_salary = None
    try:
        # attempt naive parse from filename tokens
        for token in filename:
            if token.isdigit():
                declared_salary = float(token)
                break
    except Exception:
        declared_salary = None

    if declared_salary:
        profile.salary_reported = declared_salary
        db.add(profile); db.commit(); db.refresh(profile)

    # call sales and underwriting again
    sales_result = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    underwriting_result = run_underwriting_agent(db, session_id, profile, sales_result, salary=profile.salary_reported)

    # Save logs & possibly offer
    log_payload = {"salary_resume": underwriting_result}
    agent_log = AgentLog(session_id=session_id, log=log_payload)
    db.add(agent_log); db.commit()

    if underwriting_result.get("approved"):
        final_offer = underwriting_result["offer"]
        offer = Offer(
            session_id=session_id,
            requested_amount=profile.desired_amount,
            amount=final_offer["amount"],
            tenure_months=final_offer["tenure_months"],
            interest_rate=final_offer["interest_rate"],
            monthly_emi=final_offer["monthly_emi"],
            status=OfferStatus.APPROVED,
            reason_summary=final_offer.get("reason_summary", ""),
            salary_slip_path=salary_slip_path
        )
        db.add(offer); db.commit(); db.refresh(offer)
        session = db.get(SimulationSession, session_id)
        session.latest_offer_id = offer.id
        session.status = SessionStatus.OFFER_GENERATED
        db.add(session); db.commit()
        return {"message": "Offer approved after salary upload", "offer": final_offer}
    else:
        session = db.get(SimulationSession, session_id)
        session.status = SessionStatus.REJECTED
        db.add(session); db.commit()
        return {"message": "Offer rejected after salary upload", "reason": underwriting_result.get("reason")}
