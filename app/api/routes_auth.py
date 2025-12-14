# app/api/routes_auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.schemas.auth_schemas import SignupIn, LoginIn, TokenOut, UserOut
from app.models.domain_models import User
from app.services.password_service import hash_password, verify_password
from app.services.jwt_service import create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(tags=["auth"])

@router.post("/auth/signup", response_model=TokenOut)
def signup(payload: SignupIn, db: Session = Depends(get_session)):
    existing = db.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    u = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    token = create_access_token({"sub": str(u.id)})
    return TokenOut(access_token=token)

@router.post("/auth/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    user = db.exec(select(User).where(User.email == form.username)).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token)

@router.get("/me", response_model=UserOut)
def auth_me(current_user: User = Depends(get_current_user)):
    return current_user