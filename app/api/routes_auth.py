from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.core.db import get_session
from app.schemas.auth_schemas import SignupIn, TokenOut, UserOut
from app.models.domain_models import User
from app.services.password_service import hash_password, verify_password
from app.services.jwt_service import create_access_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from app.services.mock_customer_service import add_customer_to_mocks
router = APIRouter(tags=["auth"])


def generate_customer_id() -> str:
    from uuid import uuid4
    return f"CUST_{uuid4().hex[:6].upper()}"


@router.post("/auth/signup", response_model=TokenOut)
def signup(payload: SignupIn, db: Session = Depends(get_session)):
    print("🔹 Signup payload:", payload)

    existing = db.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    customer_id = generate_customer_id()
    print("🆔 Generated customer_id:", customer_id)

    u = User(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        customer_id=customer_id,
    )

    db.add(u)
    db.commit()
    db.refresh(u)

    print("✅ User saved:", u.id, u.customer_id)

    token = create_access_token({"sub": u.customer_id})

    add_customer_to_mocks({
    "customer_id": customer_id,
    "name": u.name,
    "email": u.email,
    "phone": u.phone,
    "credit_score": 750,
    "pre_approved_limit": 500000,
    "income_monthly": 50000,
    "existing_emi": 0,
    "city": "Bangalore"
})
    print("🔐 JWT issued for:", u.customer_id)

    return TokenOut(access_token=token)


@router.post("/auth/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    print("🔹 Login attempt:", form.username)

    user = db.exec(select(User).where(User.email == form.username)).first()

    if not user:
        print("❌ User not found for email:", form.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form.password, user.password_hash):
        print("❌ Password mismatch for:", user.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    print("✅ Login success for:", user.customer_id)

    # ✅ FIX: use customer_id, NOT user.id
    token = create_access_token({"sub": user.customer_id})
    print("🔐 JWT issued for:", user.customer_id)

    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def auth_me(current_user: User = Depends(get_current_user)):
    print("👤 /me accessed by:", current_user.customer_id)
    return current_user
