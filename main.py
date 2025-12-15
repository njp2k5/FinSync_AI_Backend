# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from app.api import (
    routes_auth,
    routes_user,
    routes_dashboard,
    routes_chat,
    routes_sessions,
    routes_mocks,
    routes_admin,
    routes_health,
)
from app.core.db import init_db
from app.api.ai_openrouter import router as openrouter_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    app = FastAPI(title="FinSync AI Backend")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router, prefix="/api")
    app.include_router(routes_auth.router, prefix="/api")
    app.include_router(routes_user.router, prefix="/api")
    app.include_router(routes_dashboard.router, prefix="/api")
    app.include_router(routes_chat.router, prefix="/api")
    app.include_router(routes_sessions.router, prefix="/api")
    app.include_router(routes_mocks.router, prefix="/api")
    app.include_router(routes_admin.router, prefix="/api")
    app.include_router(openrouter_router)

    @app.on_event("startup")
    def on_startup():
        Path("uploads").mkdir(exist_ok=True, parents=True)
        init_db()
        print ("Application startup complete")

    return app


app = create_app()
