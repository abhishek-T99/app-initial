# Writing tests

You can make use of the three fixtures `client`, `main_client`, and `pgs` for most of your tests.

`client` gives a test client with fresh FastAPI instance. You can test libraries and helper functions using this test client. The main app routes and models are not available with this client.

`main_client` gives a test client with FastAPI instance of our project. This makes the main app routes and models available to us. This is useful for testing the main app routes and models.

Using `pgs` fixture gives you a session with test Postgres database. Use this fixture for testing database models and queries, when you don't need the app or the routes.

Usage examples are given below.

## Tests dependent on main app models and routes

Use the `main_client` fixture.

```python
class TestMyViewSet:
    def test_endpoint(self, main_client: TestClient):
        db = main_client.app.state.session
        response = main_client.post('/endpoint/', json={'key': 'value'})
```

### With custom database setup

Override the `main_client` fixture locally to pass custom session setup function.

```python
from core.db import Base
from tests.utils import get_client

def session_setup(self):
    Base.metadata.create_all(bind=session.bind)
    session.add(CustomModel(name='abc'))
    session.commit()

@pytest.fixture(scope="function")
def main_client(pg_session_maker):
    test_client = get_client(pg_session_maker, session_setup, app=main.app)
    with test_client as tst_client:
        yield tst_client
    if hasattr(test_client.app.state, "session") and test_client.app.state.session:
        test_client.app.state.session.close()

class TestMyViewSet:

    def test_get(self, main_client: TestClient):
        db = client.app.state.session
        response = client.post('/endpoint/', json={'key': 'value'})
```

## Tests independent of main app models and routes, but need the test client

*   Use the `client` fixture.
*   Useful for testing adapters, helpers, and libraries.

```python
class TestMyViewSet:
    def test_endpoint(self, client: TestClient):
        db = client.app.state.session
        response = client.post('/endpoint/', json={'key': 'value'})
```

### With custom database setup

Override the `client` fixture locally to pass custom session setup function.

```python
from tests.utils import get_client
from tests.conftest import Base


def session_setup(session):
    Base.metadata.create_all(bind=session.bind)
    session.add(CustomModel(name='abc'))
    session.commit()


@pytest.fixture(scope="function")
def client(pg_session_maker):
    test_client = get_client(pg_session_maker, session_setup)
    with test_client as tst_client:
        yield tst_client
    if hasattr(test_client.app.state, "session") and test_client.app.state.session:
        test_client.app.state.session.close()


class TestViewSet:
    def test_viewset_without_model(self, client, viewset):
        viewset_instance = OnboardingViewSet.add_to(app)
        viewset_instance.db.query()

```

## Tests that need just database

```python
from sqlalchemy.orm import Session

class TestClass:
    def test_method(self, pgs: Session)

```

## Environment variables for test

`pytest-env` package enables defining different environment variable values for tests. `pytest-env` package is included in `dev.txt` and `ci.txt` requirements files for development and CI environments respectively. The variable values can be defined in `pytest.ini` file in the root of the project.
