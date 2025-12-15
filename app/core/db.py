from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# ✅ FIX: use UPPERCASE to match config
engine = create_engine(
    settings.DATABASE_URL,
    echo=False
)

def init_db():
    SQLModel.metadata.create_all(bind=engine)

def get_session():
    with Session(engine) as session:
        yield session

