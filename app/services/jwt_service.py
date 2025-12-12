from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from jose import jwt, JWTError
from sqlmodel import Session, select
from app.models.domain_models import User
from app.core.config import settings
from app.core.db import get_session

ALGO = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGO)

def get_current_user(token: str = Depends(lambda: None), db: Session = Depends(get_session)):
    if token is None:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.exec(select(User).where(User.id == user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
