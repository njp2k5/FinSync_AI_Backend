from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
from app.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    agents: list[str] = []
    salary_slip: bool = False
    finalise: bool = False


SYSTEM_PROMPT = """
You are a professional loan sales agent for an Indian NBFC.

Your goals:
- Explain loan products clearly and concisely
- Ask only relevant questions
- Never hallucinate interest rates or eligibility
- Be polite, persuasive, and compliant with RBI guidelines
"""


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(req: ChatRequest):

    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENROUTER_API_KEY not configured"
        )

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "FinSync AI",
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": req.message}
        ],
        "temperature": 0.3
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenRouter error: {resp.text}"
        )

    data = resp.json()

    text = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )

    if not text:
        raise HTTPException(
            status_code=502,
            detail="Model returned empty response"
        )

    return ChatResponse(response=text)
