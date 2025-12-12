# app/schemas/chat_schemas.py
from pydantic import BaseModel
from typing import Optional

class ChatIn(BaseModel):
    message: str
    # optional field used in some flows to override or indicate mood/mode
    mood_override: Optional[str] = None

class ChatMessageIn(ChatIn):
    """
    Alias for ChatIn for compatibility with routes that import ChatMessageIn.
    Keeps the same fields as ChatIn.
    """
    pass
