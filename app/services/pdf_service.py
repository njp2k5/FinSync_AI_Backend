# app/services/pdf_service.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path
from datetime import datetime

def generate_sanction_pdf(output_path: str, customer_name: str, offer: dict, agent_log: dict, reference_id: str):
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 80, "FinSync AI — Sanction Letter")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 100, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}    Ref: {reference_id}")

    # Customer & Offer details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 140, f"Customer: {customer_name}")
    c.setFont("Helvetica", 10)
    y = height - 170
    lines = [
        f"Approved Amount: {offer['amount']}",
        f"Tenure (months): {offer['tenure_months']}",
        f"Interest rate (% p.a.): {offer['interest_rate']}",
        f"EMI (approx): {offer['monthly_emi']}",
        f"Status: {offer['status']}",
        f"Reason summary: {offer['reason_summary']}"
    ]
    for ln in lines:
        c.drawString(50, y, ln)
        y -= 16

    # Short agent log summary
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Audit: Agent decisions (summary)")
    y -= 18
    c.setFont("Helvetica", 9)
    # Write a few items from agent_log
    for agent, data in agent_log.items():
        display = f"{agent}: {str(data)[:120]}"
        c.drawString(50, y, display)
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 80

    c.showPage()
    c.save()
    return str(out)
