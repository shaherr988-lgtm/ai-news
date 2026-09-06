from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create all tables known to the shared declarative Base. Idempotent."""
    # Imported here (not at module top) so importing apps.core.db alone never
    # triggers loading every model module — but calling create_all_tables()
    # always sees the full set of tables registered on Base.metadata, because
    # apps.models's __init__ imports Source, Article, ArticleChunk, and DailyDigest.
    from apps.models import Base

    Base.metadata.create_all(bind=engine)
