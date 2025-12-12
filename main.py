# main.py
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# import routers
from app.api import routes_auth, routes_user, routes_dashboard, routes_chat, routes_sessions, routes_mocks, routes_admin, routes_health

def create_app():
    app = FastAPI(title="FinSync AI Backend")

    # CORS — adapt allowed origins in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # include routers — make sure each module defines `router`
    app.include_router(routes_health.router, prefix="/api")
    app.include_router(routes_auth.router, prefix="/api")
    app.include_router(routes_user.router, prefix="/api")
    app.include_router(routes_dashboard.router, prefix="/api")
    app.include_router(routes_chat.router, prefix="/api")
    app.include_router(routes_sessions.router, prefix="/api")
    app.include_router(routes_mocks.router, prefix="/api")
    app.include_router(routes_admin.router, prefix="/api")

    @app.on_event("startup")
    def on_startup():
        # ensure upload dir exists
        Path("uploads").mkdir(exist_ok=True, parents=True)
        # init_db() call if you have it
        try:
            from app.core.db import init_db
            init_db()
        except Exception:
            # swallow here; startup logs will show real error
            pass

    return app

app = create_app()

