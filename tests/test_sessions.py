import json
import uuid
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure a fresh test database so that schema changes (like new columns) are applied
db_path = Path(__file__).resolve().parents[1] / "finsync.db"
if db_path.exists():
    try:
        db_path.unlink()
    except Exception:
        pass

from main import app
import os
from sqlmodel import Session, select
from app.core.db import engine
from app.models.domain_models import UserProfile, Offer, OfferStatus

from main import app


client = TestClient(app)


def make_profile(name="Alice", customer_id=None):
    return {
        "customer_id": customer_id,
        "name": name,
        "age": 30,
        "income_monthly": 50000.0,
        "existing_emi": 500.0,
        "employment_type": "salaried",
        "loan_type": "personal loan",
        "desired_amount": 100000.0,
        "desired_tenure_months": 24,
        "mood": "calm",
        "email": "alice@example.com",
    }


def test_start_creates_session():
    resp = client.post("/api/sessions/start?customer_id=CUST_ALICE", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["status"] == "in_progress"
    assert data.get("customer_id") == "CUST_ALICE"


def test_start_with_customer_id_query_param():
    cust = "CUST_62EBFC"
    profile = make_profile(name="Bob")
    resp = client.post(f"/api/sessions/start?customer_id={cust}", json=profile)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data

    # fetch the session summary and verify session.customer_id persisted
    sid = data["session_id"]
    summary = client.get(f"/api/sessions/{sid}")
    assert summary.status_code == 200
    sdata = summary.json()
    assert sdata["session"].get("customer_id") == cust


def test_post_message_endpoint():
    # create session
    start = client.post("/api/sessions/start?customer_id=CUST_MSG", json={})
    sid = start.json()["session_id"]

    msg = {"sender": "user", "text": "Hello, I want a loan"}
    resp = client.post(f"/api/sessions/{sid}/message", json=msg)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert "reply" in data and "text" in data["reply"]


def test_message_without_google_api_returns_fallback():
    # Ensure message endpoint returns fallback reply when model unavailable
    start = client.post("/api/sessions/start?customer_id=CUST_FALLBACK", json={})
    sid = start.json()["session_id"]
    msg = {"sender": "user", "text": "Test fallback response"}
    resp = client.post(f"/api/sessions/{sid}/message", json=msg)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data and data["reply"]["text"].startswith("(fallback") or "Sorry" in data["reply"]["text"]


def test_get_messages_list():
    start = client.post("/api/sessions/start?customer_id=CUST_MSGS", json={})
    sid = start.json()["session_id"]
    # post two messages
    client.post(f"/api/sessions/{sid}/message", json={"sender":"user","text":"First"})
    client.post(f"/api/sessions/{sid}/message", json={"sender":"user","text":"Second"})

    resp = client.get(f"/api/sessions/{sid}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data and len(data["messages"]) >= 2


def test_upload_salary_and_resume_underwriting():
    # create session for a customer with high pre-approved limit
    cust = "CUST_62EBFC"
    start = client.post(f"/api/sessions/start?customer_id={cust}", json={})
    sid = start.json()["session_id"]

    # update profile to request some amount under pre-approved
    with Session(engine) as db:
        sid_uuid = uuid.UUID(sid)
        profile = db.exec(select(UserProfile).where(UserProfile.session_id == sid_uuid)).first()
        profile.desired_amount = 100000.0
        profile.desired_tenure_months = 12
        db.add(profile); db.commit()

    # upload salary file with declared_salary field
    files = {"file": ("salary.pdf", b"dummy-pdf-content", "application/pdf")}
    data = {"declared_salary": "45000"}
    resp = client.post(f"/api/sessions/{sid}/upload-salary", files=files, data=data)
    assert resp.status_code == 200
    j = resp.json()
    assert "Offer" in (j.get("message", "")) or "offer" in j or "Offer approved" in j.get("message", "")


def test_finalize_and_get_sanction_letter():
    start = client.post("/api/sessions/start?customer_id=CUST_FINAL", json={})
    sid = start.json()["session_id"]

    # Ensure we have a profile with desired_amount
    with Session(engine) as db:
        sid_uuid = uuid.UUID(sid)
        profile = db.exec(select(UserProfile).where(UserProfile.session_id == sid_uuid)).first()
        profile.desired_amount = 50000.0
        profile.desired_tenure_months = 12
        profile.name = "Final Test"
        db.add(profile); db.commit()

    # finalize as approved
    resp = client.post(f"/api/sessions/{sid}/finalize", data={"approved": "true"})
    assert resp.status_code == 200
    j = resp.json()
    assert j.get("message") == "finalized"

    # now request sanction letter
    resp2 = client.get(f"/api/sessions/{sid}/sanction-letter")
    assert resp2.status_code == 200
    assert resp2.headers.get("content-type") == "application/pdf"


def test_google_api_integration_monkeypatch(monkeypatch):
    # Simulate having GOOGLE_API_KEY and a working genai.GenerativeModel
    os.environ["GOOGLE_API_KEY"] = "fakekey"

    class FakeResp:
        def __init__(self, text):
            self.text = text

    class FakeModel:
        def __init__(self, model_name):
            self.model_name = model_name
        def generate_content(self, prompt):
            return FakeResp('{"Response":"Hello from model","Agents":[],"Salary_slip":false,"Finalise":false}')

    monkeypatch.setattr("app.services.chat_service.genai.GenerativeModel", FakeModel)

    start = client.post("/api/sessions/start?customer_id=CUST_GEN", json={})
    sid = start.json()["session_id"]

    resp = client.post(f"/api/sessions/{sid}/message", json={"sender":"user","text":"Hi"})
    assert resp.status_code == 200
    j = resp.json()
    assert j["reply"]["text"] == "Hello from model"


def test_admin_endpoints_basic():
    # create a session so there is something to list
    start = client.post("/api/sessions/start?customer_id=ADMIN_TEST", json={})
    sid = start.json()["session_id"]

    # list sessions
    resp = client.get("/api/admin/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data

    # agent logs (none exist yet)
    resp2 = client.get(f"/api/admin/sessions/{sid}/agent-log")
    assert resp2.status_code == 200
    assert "logs" in resp2.json()

    # rerun agents with empty agents list
    resp3 = client.post(f"/api/admin/sessions/{sid}/rerun-agents", json={"agents": ["sales", "verification"]})
    # the endpoint expects a JSON body with 'agents' as list; but route signature uses positional 'agents', so we send as raw JSON array
    resp3 = client.post(f"/api/admin/sessions/{sid}/rerun-agents", json=["sales","verification"]) 
    assert resp3.status_code == 200

    # smtp test should return sent: False since env not configured
    resp4 = client.post("/api/admin/smtp/test?to_email=test@example.com")
    assert resp4.status_code == 200
    body = resp4.json()
    assert "sent" in body


def test_mocks_endpoints():
    # list customers
    resp = client.get("/api/mocks/customers")
    assert resp.status_code == 200
    data = resp.json()
    assert "customers" in data and len(data["customers"]) > 0

    # pick a known customer from seed data
    c_id = data["customers"][0]["customer_id"]
    resp2 = client.get(f"/api/mocks/offer/{c_id}")
    assert resp2.status_code in (200, 404)

    resp3 = client.get(f"/api/mocks/crm/{c_id}")
    assert resp3.status_code == 200
    crm = resp3.json()
    assert "name" in crm

    resp4 = client.get(f"/api/mocks/credit/{c_id}")
    assert resp4.status_code == 200
    assert "credit_score" in resp4.json()


def test_dashboard_endpoint(monkeypatch):
    # Create a test user and profile in DB and monkeypatch get_current_user
    from app.core.db import engine
    from sqlmodel import Session, select
    from app.models.domain_models import User, UserProfile

    with Session(engine) as db:
        user = User(customer_id="DASH_1", name="Dash User", email="dash@example.com")
        db.add(user); db.commit(); db.refresh(user)

        profile = UserProfile(
            session_id=uuid.uuid4(),
            customer_id="DASH_1",
            name="Dash User",
            age=40,
            income_monthly=60000,
            existing_emi=2000,
            employment_type="salaried",
            loan_type="personal loan",
            desired_amount=100000,
            desired_tenure_months=12,
        )
        db.add(profile); db.commit(); db.refresh(profile)

    # Monkeypatch the dependency used in routes_dashboard
    monkeypatch.setattr("app.api.routes_dashboard.get_current_user", lambda: user)

    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("customer_id") == "DASH_1"


def test_chat_endpoints_message_and_upload():
    # create session
    start = client.post("/api/sessions/start?customer_id=CUST_CHAT", json={})
    sid = start.json()["session_id"]

    # chat message route
    resp = client.post(f"/api/chat/{sid}/message", json={"sender":"user","text":"Hello chat"})
    assert resp.status_code == 200
    assert "reply" in resp.json()

    # chat upload salary route
    files = {"file": ("salary.pdf", b"dummy", "application/pdf")}
    resp2 = client.post(f"/api/chat/{sid}/upload-salary", files=files)
    assert resp2.status_code == 200
