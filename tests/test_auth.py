
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base
from backend.db.session import get_db
from backend.main import app


# Use an isolated in-memory database for tests.
# These tests will not create or delete records in your real database.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_user(client, email="test@example.com"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )


def login_user(client, email="test@example.com"):
    return client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )


def test_register_user(client):
    response = register_user(client)

    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert response.json()["is_active"] is True
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_registration(client):
    first_response = register_user(client)
    second_response = register_user(client)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_success(client):
    register_user(client)
    response = login_user(client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_wrong_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_get_me_with_valid_token(client):
    register_user(client)
    login_response = login_user(client)
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_get_me_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_get_me_with_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401
