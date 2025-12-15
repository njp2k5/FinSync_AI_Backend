# app/services/chat_service.py
import os
import json
import uuid
from sqlmodel import Session, select
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

from app.models.domain_models import (
    SimulationSession, Message, Offer, AgentLog, SessionStatus, OfferStatus, UserProfile
)
from app.agents.emotion_agent import run_emotion_agent
from app.agents.sales_agent import run_sales_agent
from app.agents.verification_agent import run_verification_agent
from app.agents.underwriting_agent import run_underwriting_agent
from app.services.utils import save_message
from app.services.pdf_service import generate_sanction_pdf
from app.services.pdf_mailer import augment_pdf_with_pypdf, send_email_smtp
from app.schemas.session_schemas import UserProfileCreate

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST"),
    "port": int(os.getenv("SMTP_PORT") or 587),
    "user": os.getenv("SMTP_USER"),
    "password": os.getenv("SMTP_PASS"),
    "sender": os.getenv("SENDER_EMAIL")
}

# --- helper: call Google chat API ---
def call_google_chat_api(prompt: str, model: str = "gemini-1.5-flash") -> Dict[str, Any]:
    """
    Call Google Generative Chat API via `google.generativeai`.
    Uses `genai.GenerativeModel` for compatibility with Gemini models.
    """
    # If API key not set, provide a deterministic fallback to avoid breaking flows.
    if not GOOGLE_API_KEY:
        # Basic fallback: return simple JSON that mimics the model schema
        return {
            "Response": "(fallback) Thank you — we've noted your request and will proceed.",
            "Agents": [],
            "Salary_slip": False,
            "Finalise": False,
        }

    # System instruction (The Persona)
    system_instruction = (
        "You are an emotionally-aware, empathetic yet analytical loan sanctioning agent. "
        "RETURN STRICT JSON only. Do not wrap in markdown."
    )
    
    # Combine system instruction with user prompt for robust context handling
    full_prompt = f"{system_instruction}\n\n{prompt}"

    try:
        # Instantiate the model (defaults to a lightweight Gemini model if not specified)
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(full_prompt)
        text = response.text if response and response.text else ""
    except Exception as e:
        # If the external API fails, return a reasonable fallback instead of raising
        return {
            "Response": f"(fallback due to model error) Sorry, I'm temporarily unable to access the model ({e}).",
            "Agents": [],
            "Salary_slip": False,
            "Finalise": False,
        }

    # The model must return plain JSON. Try to locate a JSON block in `text`.
    text = text.strip()
    
    # Clean up markdown code blocks if present
    if "```" in text:
        # Extract content between the first and last triple backticks
        parts = text.split("```")
        # Usually the content is in the second part (index 1) if formatted like ```json ... ```
        # We iterate to find the part that looks like JSON
        for part in parts:
            clean_part = part.strip()
            if clean_part.startswith("json"):
                clean_part = clean_part[4:].strip()
            if clean_part.startswith("{") and clean_part.endswith("}"):
                text = clean_part
                break
    
    # Fallback: find first '{' and last '}'
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        json_text = text[first:last+1]
    else:
        json_text = text

    try:
        model_json = json.loads(json_text)
    except Exception:
        # If we couldn't parse JSON from the model, return a fallback response
        return {
            "Response": "(fallback) I couldn't parse the model's response clearly, but I can continue.",
            "Agents": [],
            "Salary_slip": False,
            "Finalise": False,
        }

    # Validate required keys and fallback if missing
    required = {"Response", "Agents", "Salary_slip", "Finalise"}
    if not required.issubset(set(model_json.keys())):
        # Provide deterministic partial response rather than failing
        return {
            "Response": model_json.get("Response", "(fallback) Incomplete model response."),
            "Agents": model_json.get("Agents", []),
            "Salary_slip": bool(model_json.get("Salary_slip", False)),
            "Finalise": bool(model_json.get("Finalise", False)),
        }

    return model_json


def resume_underwriting_after_salary(db: Session, session_id: UUID, salary_slip_path: str):
    """
    Called after a salary slip upload. Attaches a declared salary to the UserProfile
    when possible (or uses filename parsing), re-runs sales + underwriting, and
    persists offer or rejection accordingly.
    """
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    # try to parse declared salary from filename if not set
    declared_salary = None
    try:
        # naive parse: simple digit extraction
        filename = salary_slip_path.split(os.sep)[-1]
        for token in filename.split("_"):
            if token.isdigit():
                val = float(token)
                # arbitrary sanity check to avoid parsing IDs as salary
                if val > 1000: 
                    declared_salary = val
                break
    except Exception:
        declared_salary = None

    if declared_salary and (not profile.salary_reported):
        profile.salary_reported = declared_salary
        db.add(profile); db.commit(); db.refresh(profile)

    # re-run sales and underwriting
    sales_result = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    underwriting_result = run_underwriting_agent(db, session_id, profile, sales_result, salary=profile.salary_reported)

    # Save a short agent log about resume
    log_payload = {"salary_resume": underwriting_result, "salary_slip_path": salary_slip_path}
    agent_log = AgentLog(session_id=session_id, log=log_payload)
    db.add(agent_log); db.commit()

    if underwriting_result.get("approved"):
        final_offer = underwriting_result["offer"]
        offer = Offer(
            session_id=session_id,
            requested_amount=profile.desired_amount,
            amount=final_offer["amount"],
            tenure_months=final_offer["tenure_months"],
            interest_rate=final_offer["interest_rate"],
            monthly_emi=final_offer["monthly_emi"],
            status=OfferStatus.APPROVED,
            reason_summary=final_offer.get("reason_summary", ""),
            salary_slip_path=salary_slip_path
        )
        db.add(offer); db.commit(); db.refresh(offer)
        
        session = db.get(SimulationSession, session_id)
        # be tolerant if DB schema doesn't include this column
        if hasattr(session, "latest_offer_id"):
            session.latest_offer_id = offer.id
        session.status = SessionStatus.OFFER_GENERATED
        db.add(session); db.commit()
        return {"message": "Offer approved after salary upload", "offer": final_offer}

    # else rejected
    session = db.get(SimulationSession, session_id)
    session.status = SessionStatus.REJECTED
    db.add(session); db.commit()
    return {"message": "Offer rejected after salary upload", "reason": underwriting_result.get("reason")}


# --- helper: build prompt (strict format) ---
def build_prompt(profile: UserProfile, conversation_history: List[Dict[str, str]], agent_lines: List[str]) -> str:
    persona_context = (
        "Review the agent inputs and the customer conversation. "
        "Decide the next response to the user. "
        "If underwriting is approved or rejected, explain why gently. "
        "If more info is needed, ask for it."
    )
    conv = ""
    for m in conversation_history[-6:]:  # last few messages
        conv += f"{m['sender']}: \"{m['text']}\"\n"
    
    agents_block = "\n".join(agent_lines)
    
    schema = (
        "Return STRICT JSON only (no markdown) with this structure:\n"
        '{ "Response": "text string to user", "Agents": ["list", "of", "agents"], "Salary_slip": boolean, "Finalise": boolean }\n'
        'Set "Salary_slip": true only if underwriting explicitly requires it.\n'
        'Set "Finalise": true only if the loan is approved and ready for sanction.'
    )
    
    prompt = (
        f"{persona_context}\n\n"
        f"Customer profile: name={profile.name}, income={profile.income_monthly}, emi={profile.existing_emi}\n\n"
        f"Conversation:\n{conv}\n\n"
        f"Agent Status:\n{agents_block}\n\n"
        f"{schema}\n"
    )
    return prompt


def rerun_agents_for_session(db: Session, session_id: UUID, agents: list):
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    results = {}
    if "sales" in agents:
        results["sales"] = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    if "verification" in agents:
        results["verification"] = run_verification_agent(db, session_id, profile.customer_id)
    if "underwriting" in agents:
        sales = results.get("sales") or run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
        results["underwriting"] = run_underwriting_agent(db, session_id, profile, sales)
    return results


# --- main function ---
def handle_user_message(db: Session, session_id: UUID, message):
    session = db.get(SimulationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # save user message
    # We use 'message.text' assuming 'message' is a Pydantic model with a 'text' field
    save_message(db, session_id, "user", message.text)

    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # 1. emotion
    emotion_res = run_emotion_agent(message.text, mood_override=message.mood_override)

    # 2. run agents
    sales_res = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    verification_res = run_verification_agent(db, session_id, profile.customer_id)
    underwriting_res = run_underwriting_agent(db, session_id, profile, sales_res)

    agent_lines = [
        f'Sales: "{sales_res.get("proposed_amount")} for {sales_res.get("tenure_months")}m @ {sales_res.get("interest_rate")}%"',
        f'Verification: "{ "passed" if verification_res.get("verified") else "issues: " + str(verification_res.get("reason","unknown")) }"',
        f'Underwriting: "{underwriting_res.get("reason", underwriting_res.get("offer",{}).get("reason_summary", "ok"))}"'
    ]
    
    # Optional compliance check
    if underwriting_res.get("approved") is False:
        agent_lines.append(f'Compliance: "Decision: {underwriting_res.get("reason")}"')

    # Fetch conversation history
    msgs = db.exec(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
    conversation_history = [{"sender": m.sender, "text": m.text} for m in msgs]

    # 3. Build prompt and call Google chat API
    prompt = build_prompt(profile, conversation_history, agent_lines)

    log_payload = {
        "emotion_agent": emotion_res,
        "sales_agent": sales_res,
        "verification_agent": verification_res,
        "underwriting_agent": underwriting_res,
        "agent_lines": agent_lines,
    }

    try:
        # Use a valid Gemini model. Fallback to gemini-1.5-flash if env var is missing/invalid.
        model_name = os.getenv("GOOGLE_MODEL", "gemini-1.5-flash")
        model_json = call_google_chat_api(prompt, model=model_name)
    except Exception as e:
        log_payload["model_error"] = str(e)
        agent_log = AgentLog(session_id=session_id, log=log_payload)
        db.add(agent_log); db.commit()
        
        reply_text = "Sorry, I'm temporarily unable to process that. Please try again."
        save_message(db, session_id, "bot", reply_text)
        return {"session_id": session_id, "reply": {"text": reply_text}, "internal_log": log_payload}

    # Add response to log
    log_payload["model_response"] = model_json
    agent_log = AgentLog(session_id=session_id, log=log_payload)
    db.add(agent_log); db.commit(); db.refresh(agent_log)

    # Respond to user
    bot_text = model_json.get("Response", "I have processed your request.")
    save_message(db, session_id, "bot", bot_text)

    # Handle Salary Slip Request
    if model_json.get("Salary_slip"):
        session.status = SessionStatus.AWAITING_SALARY
        db.add(session); db.commit()
        return {
            "session_id": session_id, 
            "reply": {"text": bot_text, "next_action": "require_salary_upload"}, 
            "internal_log": log_payload
        }

    # Handle Finalization
    if model_json.get("Finalise"):
        final_offer = underwriting_res.get("offer") or {
            "amount": sales_res.get("proposed_amount"),
            "tenure_months": sales_res.get("tenure_months"),
            "interest_rate": sales_res.get("interest_rate"),
            "monthly_emi": 0,
            "reason_summary": "finalised by agent-model"
        }
        
        offer = Offer(
            session_id=session_id,
            requested_amount=profile.desired_amount,
            amount=final_offer["amount"],
            tenure_months=final_offer["tenure_months"],
            interest_rate=final_offer["interest_rate"],
            monthly_emi=final_offer["monthly_emi"],
            status=OfferStatus.APPROVED,
            reason_summary=final_offer.get("reason_summary","")
        )
        db.add(offer); db.commit(); db.refresh(offer)
        
        session.latest_offer_id = offer.id
        session.status = SessionStatus.COMPLETED
        db.add(session); db.commit()

        # Generate PDF
        reference_id = str(uuid.uuid4())[:8]
        pdf_path = f"uploads/{session_id}/sanction_{reference_id}.pdf"
        try:
            generate_sanction_pdf(pdf_path, profile.name, final_offer, log_payload, reference_id)
            augment_pdf_with_pypdf(pdf_path, {"ref": reference_id, "customer": profile.name})
        except Exception as e:
            log_payload["pdf_error"] = str(e)

        # Send Email
        if profile and getattr(profile, "email", None):
            try:
                send_email_smtp(
                    smtp_config=SMTP_CONFIG,
                    to_email=profile.email,
                    subject=f"FinSync Sanction Letter [{reference_id}]",
                    body=f"Dear {profile.name},\n\nPlease find attached your sanction letter.\nRef: {reference_id}",
                    attachments=[pdf_path] if os.path.exists(pdf_path) else [],
                )
            except Exception as e:
                log_payload["email_error"] = str(e)

        return {
            "session_id": session_id, 
            "reply": {"text": bot_text, "is_final_offer": True, "final_offer": final_offer}, 
            "internal_log": log_payload
        }

    return {"session_id": session_id, "reply": {"text": bot_text}, "internal_log": log_payload}
