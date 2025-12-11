# main.py
from fastapi import FastAPI
from app.core.db import init_db
from app.api.routes_health import router as health_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_mocks import router as mocks_router
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

def create_app() -> FastAPI:
    app = FastAPI(title="FinSync AI Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(mocks_router, prefix="/api")

    @app.on_event("startup")
    def on_startup():
        init_db()
        # make uploads dir
        Path("uploads").mkdir(exist_ok=True)

    return app

app = create_app()

