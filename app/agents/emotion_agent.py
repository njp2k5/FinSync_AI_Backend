def run_emotion_agent(text: str, mood_override: str | None = None) -> dict:
    if mood_override:
        return {"sentiment": mood_override, "evidence": "user-selected"}

    lowered = text.lower()
    if any(w in lowered for w in ["urgent", "emergency", "worried"]):
        return {"sentiment": "stressed", "evidence": "found urgent/worried keywords"}
    return {"sentiment": "calm", "evidence": "no stress keywords"}
