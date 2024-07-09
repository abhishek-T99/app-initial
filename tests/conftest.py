from typing import Any

import psycopg2
import pytest
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import as_declarative, sessionmaker

from core.db import Base as CoreBase
from tests.utils import get_client


@as_declarative()
class Base:
    id: Any
    __name__: str
    metadata: Any

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


@pytest.fixture(scope="module", autouse=True)
def pg_session_maker(postgresql_proc):
    janitor = DatabaseJanitor(
        user=postgresql_proc.user,
        host=postgresql_proc.host,
        port=postgresql_proc.port,
        dbname="test_database",
        version=postgresql_proc.version,
        password="secret_password",
    )
    janitor.init()

    connection = psycopg2.connect(
        dbname="test_database",
        user=postgresql_proc.user,
        password="secret_password",
        host=postgresql_proc.host,
        port=postgresql_proc.port,
    )
    engine = create_engine("postgresql+psycopg2://", creator=lambda: connection)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    from core.db import session

    session.SessionLocal = SessionLocal
    yield SessionLocal
    janitor.drop()


@pytest.fixture(scope="module")
def pgs(pg_session_maker):
    session = pg_session_maker()
    CoreBase.metadata.create_all(session.get_bind())
    Base.metadata.create_all(session.get_bind())
    yield session
    session.close()


def session_setup(session):
    CoreBase.metadata.create_all(bind=session.bind)
    Base.metadata.create_all(session.get_bind())


@pytest.fixture(scope="function")
def main_client(pg_session_maker):
    from core import gateway

    client = get_client(pg_session_maker, session_setup, app=gateway.app)
    with client as test_client:
        yield test_client
    if hasattr(client.app.state, "session") and client.app.state.session:
        client.app.state.session.close()


@pytest.fixture(scope="function")
def client(pg_session_maker):
    client = get_client(pg_session_maker, session_setup)
    with client as test_client:
        yield test_client
    if hasattr(client.app.state, "session") and client.app.state.session:
        client.app.state.session.close()
