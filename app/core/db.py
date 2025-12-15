from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# ✅ FIX: snake_case attribute
engine = create_engine(
    settings.database_url,
    echo=False
)

def init_db():
    SQLModel.metadata.create_all(bind=engine)

def get_session():
    with Session(engine) as session:
        yield session
