import uuid
from fastapi.testclient import TestClient
import pytest
from apps.backoffice.models import StaffUser
from core import gateway
from core.db import Base as CoreBase
from tests.utils import get_client
from apps.backoffice.helpers import generate_hash


password = generate_hash("TestPW123!@#")


def session_setup(session):
    CoreBase.metadata.create_all(bind=session.bind)
    session.add_all(
        [
            StaffUser(
                id=uuid.UUID("76e6b034-3db3-4fea-a7ab-3c1973504901"),
                role="Backoffice",
                name="Backoffice Admin",
                username="boadmin@admin.com",
                password=password,
                password_history=[password] * 5,
                phone_number="60984019692",
                status="Active",
                status_remarks="My user",
                force_change_password=True,
            )
        ]
    )
    session.commit()


@pytest.fixture(scope="module")
def main_client(pg_session_maker):
    client = get_client(pg_session_maker, session_setup, app=gateway.app)
    with client as test_client:
        yield test_client
    if hasattr(client.app.state, "session") and client.app.state.session:
        client.app.state.session.close()


class TestStaffUserViewSet:
    def test_staff_user_create(self, main_client: TestClient):
        response = main_client.post(
            url="onboarding/manage/user/staff-user",
            json ={
                "role": "Backoffice",
                "name": "BOUSER",
                "username": "user@example.com",
                "phone_number": "string",
                "status": "Active",
                "status_remarks": "string",
            },
        )
        assert response.status_code == 201

    def test_staff_user_list(self, main_client: TestClient):
        response = main_client.get(
            url="onboarding/manage/user/staff-user",
        )
        assert response.status_code == 200

    def test_staff_user_retrieve(self, main_client: TestClient):
        response = main_client.get(
            url="onboarding/manage/user/staff-user/?id=76e6b034-3db3-4fea-a7ab-3c1973504901",
        )
        assert response.status_code == 200

    def test_staff_user_delete(self, main_client: TestClient):
        response = main_client.delete(
            url="onboarding/manage/user/staff-user/76e6b034-3db3-4fea-a7ab-3c1973504901",
        )
        assert response.status_code == 204