# app/api/routes_chat.py
# app/api/routes_chat.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from uuid import UUID
from sqlmodel import Session

from app.core.db import get_session
from app.services.chat_service import (
    handle_user_message,
    resume_underwriting_after_salary,
    rerun_agents_for_session
)
from app.schemas.session_schemas import ChatMessageIn

router = APIRouter(prefix="/chat", tags=["chat"])

# 1. Send message to agents + Google LLM
@router.post("/{session_id}/message")
def chat_message(session_id: UUID, payload: ChatMessageIn, db: Session = Depends(get_session)):
    return handle_user_message(db, session_id, payload)

# 2. Resume underwriting after salary slip upload
@router.post("/{session_id}/upload-salary")
def upload_salary_slip(session_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_session)):
    save_path = f"uploads/{session_id}_{file.filename}"
    with open(save_path, "wb") as f:
        f.write(file.file.read())
    return resume_underwriting_after_salary(db, session_id, save_path)

# 3. Rerun agents for debugging (admin)
@router.post("/{session_id}/rerun-agents")
def rerun_agents(session_id: UUID, db: Session = Depends(get_session)):
    return rerun_agents_for_session(db, session_id)
