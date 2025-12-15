# app/api/routes_admin.py
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Union
from sqlmodel import Session, select
from uuid import UUID
import os
from app.core.db import get_session
from app.models.domain_models import AgentLog, SimulationSession, Offer, UserProfile
from app.services.chat_service import rerun_agents_for_session

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_session)):
    rows = db.exec(select(SimulationSession)).all()
    return {"sessions": rows}

@router.get("/sessions/{session_id}/agent-log")
def get_agent_logs(session_id: UUID, db: Session = Depends(get_session)):
    logs = db.exec(select(AgentLog).where(AgentLog.session_id == session_id).order_by(AgentLog.created_at)).all()
    return {"logs": [ {"created_at": l.created_at, "log": l.log} for l in logs ]}

@router.get("/sessions/{session_id}/last-prompt")
def last_prompt(session_id: UUID, db: Session = Depends(get_session)):
    # fetch last AgentLog entry and return stored prompt if present
    al = db.exec(select(AgentLog).where(AgentLog.session_id == session_id).order_by(AgentLog.created_at.desc())).first()
    if not al:
        raise HTTPException(status_code=404, detail="no logs")
    return {"last_log": al.log}

@router.post("/sessions/{session_id}/rerun-agents")
def rerun_agents(session_id: UUID, agents: Union[List[str], dict] = Body(...), db: Session = Depends(get_session)):
    # Accept either a raw list body ["sales", "verification"] or a dict {"agents": [...]}.
    if isinstance(agents, dict):
        agents_list = agents.get("agents") or agents.get("agents_list") or []
    else:
        agents_list = agents

    if not isinstance(agents_list, list):
        raise HTTPException(status_code=400, detail="agents must be a list of agent names")

    # rerun specific agents for debugging; uses helper from chat_service
    return rerun_agents_for_session(db=db, session_id=session_id, agents=agents_list)

@router.post("/smtp/test")
def smtp_test(to_email: str):
    # sends test email using SMTP env vars
    from app.services.pdf_mailer import send_email_smtp
    smtp_cfg = {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT") or 587),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASS"),
        "sender": os.getenv("SENDER_EMAIL")
    }
    try:
        send_email_smtp(smtp_config=smtp_cfg, to_email=to_email, subject="FinSync SMTP test", body="This is a test email from FinSync backend", attachments=[])
        return {"sent": True}
    except Exception as e:
        return {"sent": False, "error": str(e)}
