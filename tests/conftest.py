import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.models import Base


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite DB per test — fast, no external Postgres needed."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
