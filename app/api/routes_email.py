from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import httpx
import os

router = APIRouter(prefix="/api/email", tags=["email"])


class LoanConfirmationIn(BaseModel):
    name: str
    age: int
    loan_amount: float
    emi: float
    interest_rate: float
    tenure_months: int
    email: EmailStr


async def send_email_resend(payload: LoanConfirmationIn):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("SENDER_EMAIL")

    if not api_key or not sender:
        raise Exception("Resend email is not configured")

    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Loan Confirmation – FinSync</h2>

        <p>Dear <strong>{payload.name}</strong>,</p>

        <p>
            We are pleased to inform you that your loan request has been
            <strong>successfully approved</strong>. Below are the details of your loan:
        </p>

        <table style="border-collapse: collapse;">
            <tr>
                <td><strong>Name</strong></td>
                <td>: {payload.name}</td>
            </tr>
            <tr>
                <td><strong>Age</strong></td>
                <td>: {payload.age}</td>
            </tr>
            <tr>
                <td><strong>Loan Amount</strong></td>
                <td>: ₹{payload.loan_amount:,.2f}</td>
            </tr>
            <tr>
                <td><strong>EMI</strong></td>
                <td>: ₹{payload.emi:,.2f}</td>
            </tr>
            <tr>
                <td><strong>Interest Rate</strong></td>
                <td>: {payload.interest_rate}% per annum</td>
            </tr>
            <tr>
                <td><strong>Tenure</strong></td>
                <td>: {payload.tenure_months} months</td>
            </tr>
        </table>

        <p>
            Our team will contact you shortly for further formalities.
            If you have any questions, feel free to reply to this email.
        </p>

        <p>
            Warm regards,<br/>
            <strong>FinSync Loan Services</strong>
        </p>
    </div>
    """

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": payload.email,
                "subject": " Loan Confirmation – FinSync",
                "html": html_content,
            },
        )

        if response.status_code not in (200, 201, 202):
            raise HTTPException(
                status_code=500,
                detail=f"Email sending failed: {response.text}"
            )


@router.post("/send-loan-confirmation")
async def send_loan_confirmation(payload: LoanConfirmationIn):
    await send_email_resend(payload)
    return {
        "status": "success",
        "message": f"Loan confirmation email sent to {payload.email}"
    }
