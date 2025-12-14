from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from sqlmodel import Session, select

from app.models.domain_models import User
from app.core.config import settings
from app.core.db import get_session

ALGO = "HS256"

# This enables the Swagger "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def create_access_token(data: dict):
    """
    data MUST contain:
    {
        "sub": customer_id (str)
    }
    """
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set")

    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGO)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session),
):
    if not settings.SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration",
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])

        # ✅ SINGLE IDENTITY: customer_id
        customer_id = payload.get("sub")
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    user = db.exec(
        select(User).where(User.customer_id == customer_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user
