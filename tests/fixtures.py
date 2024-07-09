import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def main_app():
    from core import gateway

    with TestClient(gateway.app) as test_client:
        yield test_client


@pytest.fixture()
def main_client():
    from core import gateway

    with TestClient(gateway.app) as test_client:
        yield test_client
