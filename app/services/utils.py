# app/services/utils.py
from sqlmodel import Session
from app.models.domain_models import Message

def save_message(db: Session, session_id, sender: str, text: str):
    """
    Persist a chat message. Extracted to avoid circular imports.
    """
    m = Message(session_id=session_id, sender=sender, text=text)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m
