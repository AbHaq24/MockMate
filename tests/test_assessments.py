import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.assessments import generate_question
from backend.db.models import Base
from backend.db.session import get_db
from backend.main import app


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


def authenticated_client(client):
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def create_assessment(client):
    return client.post(
        "/assessments",
        json={"topic": "Python", "difficulty": "Easy"},
    )


def test_create_assessment(client):
    authenticated_client(client)

    response = create_assessment(client)

    assert response.status_code == 201
    assert response.json()["topic"] == "Python"
    assert response.json()["difficulty"] == "Easy"
    assert response.json()["questions_shown_count"] == 0
    assert response.json()["status"] == "in_progress"


def test_create_assessment_requires_authentication(client):
    response = create_assessment(client)

    assert response.status_code == 401


def test_invalid_difficulty_rejected(client):
    authenticated_client(client)

    response = client.post(
        "/assessments",
        json={"topic": "Python", "difficulty": "easy"},
    )

    assert response.status_code == 422


def test_generate_question(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    def fake_generate_question(topic, difficulty, previous_questions=None):
        return {
            "question": "What is a Python list?",
            "reference_answer": "A list is an ordered, mutable collection.",
        }

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_generate_question,
    )

    response = client.post(
        f"/assessments/{assessment['id']}/questions"
    )

    assert response.status_code == 200
    assert response.json()["question"] == "What is a Python list?"
    assert response.json()["display_number"] == 1

    details = client.get(
        f"/assessments/{assessment['id']}"
    )
    assert details.status_code == 404  # No detail endpoint exists yet.


def test_duplicate_question_is_rejected(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    def fake_generate_question(topic, difficulty, previous_questions=None):
        return {
            "question": "What is a Python list?",
            "reference_answer": "An ordered, mutable collection.",
        }

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_generate_question,
    )

    first = client.post(
        f"/assessments/{assessment['id']}/questions"
    )
    second = client.post(
        f"/assessments/{assessment['id']}/questions"
    )

    assert first.status_code == 200
    assert second.status_code == 502


def test_three_question_limit(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()
    generated_count = 0

    def fake_generate_question(topic, difficulty, previous_questions=None):
        nonlocal generated_count
        generated_count += 1
        return {
            "question": f"Unique Python question number {generated_count}?",
            "reference_answer": f"Reference answer {generated_count}.",
        }

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_generate_question,
    )

    for expected_number in range(1, 4):
        response = client.post(
            f"/assessments/{assessment['id']}/questions"
        )
        assert response.status_code == 200
        assert response.json()["display_number"] == expected_number

    fourth = client.post(
        f"/assessments/{assessment['id']}/questions"
    )

    assert fourth.status_code == 409
