# app/services/chat_service.py
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
from app.services.pdf_service import generate_sanction_pdf  # we used earlier
from app.services.pdf_mailer import augment_pdf_with_pypdf, send_email_smtp
from app.schemas.session_schemas import UserProfileCreate
  # see helper implementation below

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
     # must set in .env
SMTP_CONFIG = {
    "host": os.getenv("SMTP_HOST"),
    "port": int(os.getenv("SMTP_PORT") or 587),
    "user": os.getenv("SMTP_USER"),
    "password": os.getenv("SMTP_PASS"),
    "sender": os.getenv("SENDER_EMAIL")
}

# --- helper: call Google chat API (stubbed) ---
def call_google_chat_api(prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Call Google Generative Chat API via `google.generativeai`.

    Notes:
    - model can be changed to a model name you have access to (e.g., "chat-bison" or gpt-4o-mini).
    - This function expects the model to return a JSON string as content. We parse it and validate keys.
    - Raises ValueError on invalid/missing JSON or keys.
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set in environment")

    # Build messages array: system instruction + user content
    messages = [
        {"role": "system", "content": "You are an emotionally-aware, empathetic yet analytical loan sanctioning agent. RETURN STRICT JSON only."},
        {"role": "user", "content": prompt}
    ]

    # Call the API
    try:
        # The exact API surface can vary between versions of google-generativeai.
        # The code below follows the documented chat.create API interface.
        response = genai.chat.create(model=model, messages=messages, max_output_tokens=512)
        # Get the text content from the response safely:
        text = ""
        # new clients may expose different attributes, try safe access patterns:
        if hasattr(response, "content"):
            # some versions: response.content[0].text or response.content
            text = response.content[0].text if isinstance(response.content, (list, tuple)) else str(response.content)
        else:
            # fallback: `.last` or `.candidates`
            text = getattr(response, "last", "") or ""
            if not text and hasattr(response, "candidates"):
                c = response.candidates
                text = c[0].output if isinstance(c, (list, tuple)) else str(c)
        if not text:
            # try repr(response)
            text = str(response)

    except Exception as e:
        # bubble up as a ValueError so caller can handle/log
        raise ValueError(f"Google API call failed: {e}")

    # The model must return plain JSON. Try to locate a JSON block in `text`.
    text = text.strip()
    # If the model wraps JSON in markdown or backticks, strip them:
    if text.startswith("```"):
        # remove code block markers
        parts = text.split("```")
        # get content between first pair of backticks
        if len(parts) >= 2:
            text = parts[1].strip()
    # If the model prepended explanation, try to find the first "{" and last "}"
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        json_text = text[first:last+1]
    else:
        json_text = text

    try:
        model_json = json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from model response. Raw: {text[:400]} Error: {e}")

    # Validate required keys
    required = {"Response", "Agents", "Salary_slip", "Finalise"}
    if not required.issubset(set(model_json.keys())):
        raise ValueError(f"Model JSON missing required keys. Found keys: {list(model_json.keys())}")

    # Basic type checking
    if not isinstance(model_json["Response"], str):
        raise ValueError("Model JSON field 'Response' must be a string")
    if not isinstance(model_json["Agents"], list):
        raise ValueError("Model JSON field 'Agents' must be a list")
    if not isinstance(model_json["Salary_slip"], bool):
        raise ValueError("Model JSON field 'Salary_slip' must be a boolean")
    if not isinstance(model_json["Finalise"], bool):
        raise ValueError("Model JSON field 'Finalise' must be a boolean")

    return model_json

    # -- resume_underwriting_after_salary: re-run underwriting after salary upload --


def resume_underwriting_after_salary(db, session_id, salary_slip_path: str):
    """
    Called after a salary slip upload. Attaches a declared salary to the UserProfile
    when possible (or uses filename parsing), re-runs sales + underwriting, and
    persists offer or rejection accordingly.
    """
    # load profile
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    # try to parse declared salary from path if not set already
    declared_salary = None
    try:
        # naive parse from filename tokens: look for digits
        filename = salary_slip_path.split("_")
        for token in filename:
            if token.isdigit():
                declared_salary = float(token)
                break
    except Exception:
        declared_salary = None

    # if there's declared salary in form field, caller should have updated profile.salary_reported already;
    # otherwise use parsed value
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

    # If approved -> persist Offer and update session
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
        session.latest_offer_id = offer.id
        session.status = SessionStatus.OFFER_GENERATED
        db.add(session); db.commit()
        return {"message": "Offer approved after salary upload", "offer": final_offer}

    # else rejected
    session = db.get(SimulationSession, session_id)
    session.status = SessionStatus.REJECTED
    db.add(session); db.commit()
    return {"message": "Offer rejected after salary upload", "reason": underwriting_result.get("reason")}



    # ====== PRODUCTION EXAMPLE (pseudocode) ======
    # from google import generativeai as genai
    # genai.configure(api_key=GOOGLE_API_KEY)
    # response = genai.chat.create(model="chat-bison@001", messages=[{"role":"system","content":prompt}])
    # text = response.last  # adjust to actual response API
    # try:
    #     return json.loads(text)
    # except Exception:
    #     raise ValueError("Model did not return valid JSON")

# --- helper: build prompt (strict format) ---
def build_prompt(profile: UserProfile, conversation_history: List[Dict[str, str]], agent_lines: List[str]) -> str:
    persona = (
        "You are an emotionally aware, empathetic yet analytical loan sanctioning agent. "
        "For each query you will be provided with short lines from worker agents (Sales, Verification, Underwriting, Compliance). "
        "You will assess them and return a strict JSON only with fields: Response, Agents, Salary_slip, Finalise."
    )
    conv = ""
    for m in conversation_history[-6:]:  # last few messages
        conv += f"{m['sender']}: \"{m['text']}\"\n"
    agents_block = "\n".join(agent_lines)
    schema = (
        "Return STRICT JSON only, for example:\n"
        '{ "Response": "text", "Agents": ["compliance"], "Salary_slip": false, "Finalise": false }\n'
    )
    prompt = f"{persona}\n\nCustomer profile: name={profile.name}, income_monthly={profile.income_monthly}, existing_emi={profile.existing_emi}\n\nConversation:\n{conv}\n\nAgent messages:\n{agents_block}\n\n{schema}\nRespond now with JSON only."
    return prompt

def rerun_agents_for_session(db: Session, session_id: UUID, agents: list):
    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    results = {}
    # run selected agents
    if "sales" in agents:
        results["sales"] = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    if "verification" in agents:
        results["verification"] = run_verification_agent(db, session_id, profile.customer_id)
    if "underwriting" in agents:
        # need sales for underwriting
        sales = results.get("sales") or run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
        results["underwriting"] = run_underwriting_agent(db, session_id, profile, sales)
    return results

# --- main function ---
def handle_user_message(db: Session, session_id: UUID, message):
    session = db.get(SimulationSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # save user message
    save_message(db, session_id, "user", message.text)

    profile = db.exec(select(UserProfile).where(UserProfile.session_id == session_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    # 1. emotion
    emotion_res = run_emotion_agent(message.text, mood_override=message.mood_override)

    # 2. determine which agents to run - default all, or follow session metadata
    # For simplicity we run all relevant agents each turn
    sales_res = run_sales_agent(db, session_id, requested_amount=profile.desired_amount, tenure_months=profile.desired_tenure_months)
    verification_res = run_verification_agent(db, session_id, profile.customer_id)
    underwriting_res = run_underwriting_agent(db, session_id, profile, sales_res)

    # Build agent lines in the exact given format
    agent_lines = [
        f'Sales agent: "{sales_res.get("proposed_amount")} for {sales_res.get("tenure_months")} months at {sales_res.get("interest_rate")}% — {sales_res.get("comment","")}"',
        f'Verification agent: "{ "passed" if verification_res.get("verification_passed") else "issues: " + ",".join(verification_res.get("issues",[])) }"',
        f'Underwriting agent: "{ underwriting_res.get("reason", underwriting_res.get("offer",{}).get("reason_summary", "")) }"'
    ]
    # Add compliance line if your underwriting result included checks
    if underwriting_res.get("approved") is False and underwriting_res.get("reason"):
        agent_lines.append(f'Compliance agent: "Decision: {underwriting_res.get("reason")}"')
    else:
        agent_lines.append('Compliance agent: "okay to sanction"')

    # Fetch conversation history to include recent lines
    msgs = db.exec(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
    conversation_history = [{"sender": m.sender, "text": m.text} for m in msgs]

    # 3. Build prompt and call Google chat API
    prompt = build_prompt(profile, conversation_history, agent_lines)

    # Call Google generative chat and validate JSON output
    try:
        # you can change the model string here if required
        model_json = call_google_chat_api(prompt, model=os.getenv("GOOGLE_MODEL", "gpt-4o-mini"))
    except Exception as e:
        # persist an error log entry
        log_payload = {
            "emotion_agent": emotion_res,
            "sales_agent": sales_res,
            "verification_agent": verification_res,
            "underwriting_agent": underwriting_res,
            "agent_lines": agent_lines,
            "model_error": str(e)
        }
        agent_log = AgentLog(session_id=session_id, log=log_payload)
        db.add(agent_log); db.commit()
        # user-friendly fallback
        reply_text = "Sorry, I'm temporarily unable to process that — please try again in a moment."
        save_message(db, session_id, "bot", reply_text)
        return {"session_id": session_id, "reply": {"text": reply_text}, "internal_log": log_payload}


    # Validate model_json
    if not isinstance(model_json, dict) or "Response" not in model_json:
        reply_text = "Sorry, the assistant returned invalid format."
        save_message(db, session_id, "bot", reply_text)
        raise HTTPException(status_code=500, detail="Invalid model response")

    # Persist AgentLog for prompt and model response
    log_payload = {
        "emotion_agent": emotion_res,
        "sales_agent": sales_res,
        "verification_agent": verification_res,
        "underwriting_agent": underwriting_res,
        "agent_lines": agent_lines,
        "model_response": model_json
    }
    agent_log = AgentLog(session_id=session_id, log=log_payload)
    db.add(agent_log); db.commit(); db.refresh(agent_log)

    # Respond to user
    bot_text = model_json["Response"]
    save_message(db, session_id, "bot", bot_text)

    # If model asks for salary slip
    if model_json.get("Salary_slip"):
        session.status = SessionStatus.AWAITING_SALARY
        db.add(session); db.commit()
        return {"session_id": session_id, "reply": {"text": bot_text, "next_action": "require_salary_upload"}, "internal_log": log_payload}

    # If model finalises: generate PDF and email
    if model_json.get("Finalise"):
        # prepare offer - prefer underwriting_res["offer"] if available else sales_res
        final_offer = underwriting_res.get("offer") or {
            "amount": sales_res.get("proposed_amount"),
            "tenure_months": sales_res.get("tenure_months"),
            "interest_rate": sales_res.get("interest_rate"),
            "monthly_emi": 0,
            "reason_summary": "finalised by agent-model"
        }
        # persist offer
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

        # generate PDF
        reference_id = str(uuid.uuid4())[:8]
        pdf_path = f"uploads/{session_id}/sanction_{reference_id}.pdf"
        generate_sanction_pdf(pdf_path, profile.name, final_offer, log_payload, reference_id)
        # augment using pypdf (add metadata)
        try:
            augment_pdf_with_pypdf(pdf_path, {"ref": reference_id, "customer": profile.name})
        except Exception:
            pass

        # send email via SMTP
        if profile and getattr(profile, "email", None):
            try:
                send_email_smtp(
                    smtp_config=SMTP_CONFIG,
                    to_email=profile.email,
                    subject=f"FinSync Sanction Letter [{reference_id}]",
                    body=f"Dear {profile.name},\n\nPlease find attached your sanction letter.\nRef: {reference_id}",
                    attachments=[pdf_path],
                )
            except Exception as e:
                # log but continue
                log_payload["email_error"] = str(e)

        final_bot_text = model_json.get("Response", "Your loan has been approved. The sanction letter will be emailed to you.")
        save_message(db, session_id, "bot", final_bot_text)
        return {"session_id": session_id, "reply": {"text": final_bot_text, "is_final_offer": True, "final_offer": final_offer}, "internal_log": log_payload}

    # Default: return model response and internal log
    return {"session_id": session_id, "reply": {"text": bot_text}, "internal_log": log_payload}
