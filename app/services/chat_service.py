from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException

from app.models.domain_models import (
    SimulationSession, Message, Offer, AgentLog, OfferStatus, SessionStatus
)
from app.schemas.session_schemas import (
    ChatMessageIn, ChatResponse, ChatReply, OfferOut
)
from app.agents.emotion_agent import run_emotion_agent
from app.agents.sales_agent import run_sales_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.compliance_agent import run_compliance_agent

def handle_user_message(db: Session, session_id: UUID, message: ChatMessageIn) -> ChatResponse:
    session = db.get(SimulationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # save user message
    user_msg = Message(session_id=session_id, sender="user", text=message.text)
    db.add(user_msg)
    db.commit()

    # load messages and user profile if agents need history
    # (you can add queries here)

    # 1. emotion
    emotion_result = run_emotion_agent(message.text, mood_override=message.mood_override)
    # 2. sales
    sales_result = run_sales_agent(db, session_id)
    # 3. risk
    risk_result = run_risk_agent(db, session_id, sales_result)
    # 4. compliance
    compliance_result = run_compliance_agent(db, session_id, risk_result)

    # build final offer + log
    final_offer_data = compliance_result["offer"]
    is_approved = compliance_result["approved"]

    offer_status = OfferStatus.APPROVED if is_approved else OfferStatus.REJECTED

    offer = Offer(
        session_id=session_id,
        amount=final_offer_data["amount"],
        tenure_months=final_offer_data["tenure_months"],
        interest_rate=final_offer_data["interest_rate"],
        monthly_emi=final_offer_data["monthly_emi"],
        status=offer_status,
        reason_summary=final_offer_data["reason_summary"],
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    session.latest_offer_id = offer.id
    session.status = SessionStatus.OFFER_GENERATED if is_approved else SessionStatus.REJECTED
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()

    # construct log
    log_payload = {
        "emotion_agent": emotion_result,
        "sales_agent": sales_result,
        "risk_agent": risk_result,
        "compliance_agent": compliance_result,
    }
    agent_log = AgentLog(session_id=session_id, offer_id=offer.id, log=log_payload)
    db.add(agent_log)
    db.commit()

    # build response
    reply_text = "Here is your offer."  # later: compose better message
    reply = ChatReply(
        text=reply_text,
        is_final_offer=True,
        final_offer=OfferOut(
            amount=offer.amount,
            tenure_months=offer.tenure_months,
            interest_rate=offer.interest_rate,
            monthly_emi=offer.monthly_emi,
            status=offer.status,
            reason_summary=offer.reason_summary,
        )
    )

    # save bot message
    bot_msg = Message(session_id=session_id, sender="bot", text=reply.text)
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        internal_log=log_payload  # you can adapt to InternalLogOut schema if needed
    )
