from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from uuid import UUID

from app.core.db import get_session
from app.schemas.session_schemas import (
    UserProfileCreate,
    SessionStartResponse,
    ChatMessageIn,
    ChatResponse,
)
from app.services.session_service import start_session
from app.services.chat_service import handle_user_message

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/start", response_model=SessionStartResponse)
def create_session(
    profile: UserProfileCreate,
    db: Session = Depends(get_session),
):
    return start_session(db=db, profile=profile)

@router.post("/{session_id}/message", response_model=ChatResponse)
def send_message(
    session_id: UUID,
    message: ChatMessageIn,
    db: Session = Depends(get_session),
):
    return handle_user_message(db=db, session_id=session_id, message=message)
