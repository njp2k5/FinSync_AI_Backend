from fastapi import FastAPI
from app.core.db import init_db
from app.api.routes_health import router as health_router
from app.api.routes_sessions import router as sessions_router

def create_app() -> FastAPI:
    app = FastAPI(title="FinSync AI Backend")

    # include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")

    @app.on_event("startup")
    def on_startup():
        init_db()

    return app

app = create_app()
