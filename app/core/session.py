class SessionStore:
    _store = {}

    @classmethod
    def create_session(cls, session_id: str, financial_profile: dict):
        cls._store[session_id] = {
            "financial_profile": financial_profile
        }

    @classmethod
    def get_session(cls, session_id: str):
        return cls._store.get(session_id)
