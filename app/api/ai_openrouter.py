from fastapi import APIRouter
from pydantic import BaseModel
import httpx
import logging
from app.core.config import settings

router = APIRouter(prefix="/api/ai", tags=["AI"])

logger = logging.getLogger(__name__)

# -----------------------------
# Request / Response Schemas
# -----------------------------

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    agents: list[str] = []
    salary_slip: bool = False
    finalise: bool = False


# -----------------------------
# Prompt & Models
# -----------------------------

SYSTEM_PROMPT = (
    "You are a concise, professional representative for an Indian NBFC. "
    "Always reply in a single sentence (maximum two). "
    "Never ask the user for any information. "
    "Each response must begin with 'Sales agent says:', "
    "'Underwriting agent says:', 'Risk agent says:', or 'Compliance agent says:'. "
    "Always use a polite, persuasive tone encouraging the user to consider or take the loan."
)

# ✅ Ordered fallback (never loop back)
MODELS = [
    "arcee-ai/trinity-mini:free",
    "mistralai/mistral-7b-instruct:free",
]

# -----------------------------
# HTTP Config
# -----------------------------

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

TIMEOUT = httpx.Timeout(
    timeout=20.0,
    connect=5.0,
    read=20.0,
    write=20.0,
)

# -----------------------------
# Chat Endpoint
# -----------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(req: ChatRequest):

    if not settings.OPENROUTER_API_KEY:
        logger.warning("OpenRouter API key not configured")
        return ChatResponse(
            response="AI service is not configured at the moment."
        )

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://finsync.ai",
        "X-Title": "FinSync AI",
    }

    fallback_response = ChatResponse(
        response="I’m currently experiencing high traffic. Please try again shortly."
    )

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:

        for model in MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": req.message},
                ],
                "temperature": 0.2,
                # ✅ Increased to avoid truncation
                "max_tokens": 512,
            }

            try:
                resp = await client.post(
                    OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )

                body_snippet = (resp.text or "")[:300]
                logger.info(
                    "openrouter: model=%s status=%s body_snippet=%s",
                    model,
                    resp.status_code,
                    body_snippet,
                )

                if resp.status_code != 200:
                    continue

                data = resp.json()
                choice = (data.get("choices") or [{}])[0]

                finish_reason = choice.get("finish_reason")
                message = choice.get("message", {})
                content = (message.get("content") or "").strip()

                # ❌ Reject truncated or empty responses
                if finish_reason != "stop":
                    logger.warning(
                        "model %s returned finish_reason=%s; skipping",
                        model,
                        finish_reason,
                    )
                    continue

                if not content:
                    logger.warning("model %s returned empty content; skipping", model)
                    continue

                # ✅ SUCCESS — STOP FALLBACK CHAIN
                logger.info("model %s succeeded; returning response", model)
                return ChatResponse(response=content)

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning("network error calling model %s: %s", model, exc)
                continue

            except Exception as exc:
                logger.exception("unexpected error calling model %s", model)
                continue

    # 🔴 Only reached if ALL models failed
    logger.error("all OpenRouter models failed; returning fallback")
    return fallback_response
