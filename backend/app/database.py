from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine_args = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

auth_db = "postgresql+psycopg://postgres:postgres@db:5432/producthub"
engine = create_engine(settings.database_url or auth_db, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
