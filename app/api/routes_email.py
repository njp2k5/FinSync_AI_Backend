from fastapi import APIRouter, HTTPException
from email.message import EmailMessage
import smtplib
import os

from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/email", tags=["email"])


class LoanConfirmationIn(BaseModel):
    name: str
    age: int
    loan_amount: float
    emi: float
    interest_rate: float
    email: EmailStr


@router.post("/send-loan-confirmation")
def send_loan_confirmation(payload: LoanConfirmationIn):
    """
    Sends loan confirmation email to customer
    """

    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")

    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        raise HTTPException(
            status_code=500,
            detail="SMTP environment variables not configured"
        )

    subject = "Loan Confirmation – FinSync"

    body = f"""
Dear {payload.name},

We are pleased to confirm the details of your loan application.

📄 Loan Details:
• Name: {payload.name}
• Age: {payload.age}
• Loan Amount: ₹{payload.loan_amount:,.2f}
• EMI: ₹{payload.emi:,.2f}
• Interest Rate: {payload.interest_rate}% per annum

Your loan has been successfully processed.

If you have any questions, feel free to reply to this email.

Warm regards,
FinSync Loan Team
"""

    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = payload.email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )

    return {
        "status": "success",
        "message": f"Loan confirmation email sent to {payload.email}"
    }
