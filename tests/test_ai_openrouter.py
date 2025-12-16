import json
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class FakeResp:
    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def make_fake_client_factory(responses):
    # responses: iterable of FakeResp
    it = iter(responses)

    class FakeClient:
        def __init__(self, timeout=None):
            self._timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            return next(it)

    return FakeClient


def test_openrouter_model_fallback_order(monkeypatch):
    # First model throttles (429), second returns valid JSON
    from app.core import config

    monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "fakekey")

    r1 = FakeResp(status_code=429, text="")
    r2 = FakeResp(status_code=200, text='{"choices":[{"message":{"content":"Reply from model 2"}}]}', json_data={"choices": [{"message": {"content": "Reply from model 2"}}]})

    monkeypatch.setattr("app.api.ai_openrouter.httpx.AsyncClient", make_fake_client_factory([r1, r2]))

    resp = client.post("/api/ai/chat", json={"message": "Hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Reply from model 2"


def test_openrouter_nonjson_body_returns_text(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "fakekey")

    r = FakeResp(status_code=200, text="Plain text reply from model")
    monkeypatch.setattr("app.api.ai_openrouter.httpx.AsyncClient", make_fake_client_factory([r]))

    resp = client.post("/api/ai/chat", json={"message": "Hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Plain text reply" in data["response"]


def test_openrouter_all_models_fail_returns_fallback(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "fakekey")

    r1 = FakeResp(status_code=429, text="")
    r2 = FakeResp(status_code=502, text="Bad gateway")
    r3 = FakeResp(status_code=503, text="Service unavailable")

    monkeypatch.setattr("app.api.ai_openrouter.httpx.AsyncClient", make_fake_client_factory([r1, r2, r3]))

    resp = client.post("/api/ai/chat", json={"message": "Hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert "experiencing high traffic" in data["response"] or "try again" in data["response"].lower()
