# app/services/pdf_mailer.py
# app/services/pdf_mailer.py
from pypdf import PdfReader, PdfWriter
import smtplib, ssl
from email.message import EmailMessage
from typing import Dict, List, Optional
import os

def augment_pdf_with_pypdf(pdf_path: str, metadata: Dict[str,str]):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    writer.add_metadata({f"/{k}": str(v) for k,v in metadata.items()})
    out_path = pdf_path.replace(".pdf", "_meta.pdf")
    with open(out_path, "wb") as f:
        writer.write(f)
    os.replace(out_path, pdf_path)
    return pdf_path

def send_email_smtp(
    smtp_config: Dict,
    to_email: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    reply_to: Optional[str] = None,
    from_display_name: Optional[str] = None
):
    """
    Sends email using configured SMTP server.

    - smtp_config: {host, port, user, password, sender}
      'sender' should be the authenticated address (SENDER_EMAIL) used in SMTP login.
    - reply_to: the user's email to set as Reply-To header (safe).
    - from_display_name: optional display name to appear with 'From' header e.g. "FinSync (on behalf of Arjun)"
    """
    sender_addr = smtp_config.get("sender") or smtp_config.get("user")
    msg = EmailMessage()

    # Build 'From' header with optional display name
    if from_display_name:
        msg["From"] = f"{from_display_name} <{sender_addr}>"
    else:
        msg["From"] = sender_addr

    msg["To"] = to_email
    msg["Subject"] = subject

    # Set Reply-To to user's email if provided, otherwise not set
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(body)

    # Attach files
    for path in attachments or []:
        with open(path, "rb") as f:
            data = f.read()
        # set mime as application/pdf for PDF attachments
        maintype, subtype = ("application", "pdf")
        filename = os.path.basename(path)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls(context=context)
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)
