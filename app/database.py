from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.config import config
from app.models import Base

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + threading
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
