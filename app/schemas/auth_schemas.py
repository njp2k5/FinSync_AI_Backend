from uuid import UUID
from pydantic import BaseModel, EmailStr

class SignupIn(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str
    customer_id: str | None

    class Config:
        from_attributes = True
