from fastapi import FastAPI
from starlette.testclient import TestClient
from core.db.session import get_db


def get_client(pg_session_maker, setup_function=None, app=None):
    app_instance = app or FastAPI()
    # app_instance.state.janitor = janitor
    session = pg_session_maker()
    if setup_function is not None:
        setup_function(session)

    def override_get_db():
        try:
            app_instance.state.session = session
            yield session
        finally:
            if session is not None:
                # session.close()
                pass
            # janitor.drop()

    app_instance.state.session = session
    app_instance.dependency_overrides[get_db] = override_get_db
    return TestClient(app_instance)
