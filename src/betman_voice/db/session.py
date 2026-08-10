from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from betman_voice.core.config import get_settings

Base = declarative_base()


def _engine_args(database_url: str) -> dict:
    if database_url == "sqlite:///:memory:":
        return {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}


engine = create_engine(get_settings().database_url, **_engine_args(get_settings().database_url))
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
