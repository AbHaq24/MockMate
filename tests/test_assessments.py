
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Base,
    Evaluation,
)
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


def fake_question_generator():
    counter = {"value": 0}

    def generate(topic, difficulty, previous_questions=None):
        counter["value"] += 1
        number = counter["value"]
        return {
            "question": f"Unique Python question number {number}?",
            "reference_answer": f"Reference answer {number}.",
        }

    return generate


def generate_question_for_slot(client, assessment_id):
    return client.post(
        f"/assessments/{assessment_id}/questions"
    )


def regenerate_question(client, assessment_id, slot):
    return client.post(
        f"/assessments/{assessment_id}/questions/{slot}/regenerate"
    )


def fake_evaluation(**kwargs):
    return {
        "score": 85,
        "feedback": "Good understanding.",
        "strengths": "Correct explanation.",
        "improvements": "Add a practical example.",
    }


def submit_answer(client, assessment_id, question_id, answer_text):
    return client.post(
        f"/assessments/{assessment_id}/questions/{question_id}/answer",
        json={"answer_text": answer_text},
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

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    response = generate_question_for_slot(client, assessment["id"])

    assert response.status_code == 200
    assert response.json()["display_number"] == 1
    assert response.json()["version_number"] == 1
    assert response.json()["is_current"] is True

    # The assessment detail endpoint has not been implemented yet.
    details = client.get(f"/assessments/{assessment['id']}")
    assert details.status_code == 404


def test_duplicate_question_is_rejected(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    def duplicate_generator(topic, difficulty, previous_questions=None):
        return {
            "question": "What is a Python list?",
            "reference_answer": "An ordered, mutable collection.",
        }

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        duplicate_generator,
    )

    first = generate_question_for_slot(client, assessment["id"])
    second = generate_question_for_slot(client, assessment["id"])

    assert first.status_code == 200
    assert second.status_code == 502


def test_three_question_limit(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    for expected_number in range(1, 4):
        response = generate_question_for_slot(client, assessment["id"])
        assert response.status_code == 200
        assert response.json()["display_number"] == expected_number

    fourth = generate_question_for_slot(client, assessment["id"])
    assert fourth.status_code == 409


def test_regeneration_preserves_previous_version_and_other_slots(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    first = generate_question_for_slot(client, assessment["id"]).json()
    second = generate_question_for_slot(client, assessment["id"]).json()

    regenerated = regenerate_question(client, assessment["id"], 1)

    assert regenerated.status_code == 200
    new_version = regenerated.json()

    assert new_version["display_number"] == 1
    assert new_version["version_number"] == 2
    assert new_version["is_current"] is True
    assert new_version["question"] != first["question"]

    with TestSessionLocal() as db:
        slot_one = db.scalars(
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.assessment_id == assessment["id"],
                AssessmentQuestion.display_number == 1,
            )
            .order_by(AssessmentQuestion.version_number)
        ).all()

        slot_two = db.scalar(
            select(AssessmentQuestion).where(
                AssessmentQuestion.assessment_id == assessment["id"],
                AssessmentQuestion.display_number == 2,
                AssessmentQuestion.is_current.is_(True),
            )
        )

        assert len(slot_one) == 2
        assert [row.version_number for row in slot_one] == [1, 2]
        assert [row.is_current for row in slot_one] == [False, True]

        # Regeneration must not alter the other slot.
        assert slot_two.id == second["assessment_question_id"]

    # Regeneration does not consume another question slot.
    assessment_response = client.get(f"/assessments/{assessment['id']}")
    assert assessment_response.status_code == 404


def test_regeneration_limit_is_three_versions(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    initial = generate_question_for_slot(client, assessment["id"])
    second = regenerate_question(client, assessment["id"], 1)
    third = regenerate_question(client, assessment["id"], 1)
    fourth = regenerate_question(client, assessment["id"], 1)

    assert initial.status_code == 200
    assert initial.json()["version_number"] == 1

    assert second.status_code == 200
    assert second.json()["version_number"] == 2

    assert third.status_code == 200
    assert third.json()["version_number"] == 3

    assert fourth.status_code == 409

    with TestSessionLocal() as db:
        versions = db.scalars(
            select(AssessmentQuestion).where(
                AssessmentQuestion.assessment_id == assessment["id"],
                AssessmentQuestion.display_number == 1,
            )
        ).all()

        assert len(versions) == 3


def test_regeneration_rejected_after_answer_submission(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    generated = generate_question_for_slot(client, assessment["id"])
    assert generated.status_code == 200

    with TestSessionLocal() as db:
        answer = Answer(
            assessment_question_id=generated.json()["assessment_question_id"],
            answer_text="A Python list is ordered and mutable.",
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(answer)
        db.commit()

    response = regenerate_question(client, assessment["id"], 1)

    assert response.status_code == 409
    assert "answered" in response.json()["detail"].lower()


def test_submit_answer_successfully(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    question = generate_question_for_slot(
        client, assessment["id"]
    ).json()

    monkeypatch.setattr(
        "backend.api.assessments.evaluate_answer",
        fake_evaluation,
    )

    response = submit_answer(
        client,
        assessment["id"],
        question["assessment_question_id"],
        "A list is ordered and mutable.",
    )

    assert response.status_code == 200
    assert response.json()["score"] == 85
    assert response.json()["feedback"] == "Good understanding."

    with TestSessionLocal() as db:
        assert db.query(Answer).count() == 1
        assert db.query(Evaluation).count() == 1

        saved_assessment = db.get(Assessment, assessment["id"])
        assert saved_assessment.status == "completed"


def test_duplicate_answer_submission_rejected(client, monkeypatch):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    question = generate_question_for_slot(
        client, assessment["id"]
    ).json()

    monkeypatch.setattr(
        "backend.api.assessments.evaluate_answer",
        fake_evaluation,
    )

    first = submit_answer(
        client,
        assessment["id"],
        question["assessment_question_id"],
        "A list is mutable.",
    )
    second = submit_answer(
        client,
        assessment["id"],
        question["assessment_question_id"],
        "A list is mutable.",
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_second_question_answer_rejected_after_first_submission(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    first_question = generate_question_for_slot(
        client, assessment["id"]
    ).json()
    second_question = generate_question_for_slot(
        client, assessment["id"]
    ).json()

    evaluation_calls = {"count": 0}

    def counted_evaluation(**kwargs):
        evaluation_calls["count"] += 1
        return fake_evaluation(**kwargs)

    monkeypatch.setattr(
        "backend.api.assessments.evaluate_answer",
        counted_evaluation,
    )

    first = submit_answer(
        client,
        assessment["id"],
        first_question["assessment_question_id"],
        "My first answer.",
    )
    second = submit_answer(
        client,
        assessment["id"],
        second_question["assessment_question_id"],
        "My second answer.",
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert evaluation_calls["count"] == 1

    with TestSessionLocal() as db:
        assert db.query(Answer).count() == 1
        assert db.query(Evaluation).count() == 1
        assert db.get(Assessment, assessment["id"]).status == "completed"


def test_blank_answer_rejected(client):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    response = client.post(
        f"/assessments/{assessment['id']}/questions/1/answer",
        json={"answer_text": "   "},
    )

    assert response.status_code == 422


def test_evaluation_failure_does_not_save_answer(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    question = generate_question_for_slot(
        client, assessment["id"]
    ).json()

    def failed_evaluation(**kwargs):
        raise RuntimeError("AI service unavailable.")

    monkeypatch.setattr(
        "backend.api.assessments.evaluate_answer",
        failed_evaluation,
    )

    response = submit_answer(
        client,
        assessment["id"],
        question["assessment_question_id"],
        "A list is mutable.",
    )

    assert response.status_code == 502

    with TestSessionLocal() as db:
        assert db.query(Answer).count() == 0
        assert db.query(Evaluation).count() == 0
        assert db.get(Assessment, assessment["id"]).status == "in_progress"


def test_finish_without_answer_after_three_questions(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    for _ in range(3):
        response = generate_question_for_slot(
            client, assessment["id"]
        )
        assert response.status_code == 200

    response = client.post(
        f"/assessments/{assessment['id']}/finish"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["score"] is None

    with TestSessionLocal() as db:
        assert db.query(Answer).count() == 0
        assert db.query(Evaluation).count() == 0
        assert db.get(Assessment, assessment["id"]).status == "completed"


def test_finish_without_answer_rejected_before_three_questions(
    client, monkeypatch
):
    authenticated_client(client)
    assessment = create_assessment(client).json()

    monkeypatch.setattr(
        "backend.api.assessments.generate_question",
        fake_question_generator(),
    )

    generate_question_for_slot(client, assessment["id"])

    response = client.post(
        f"/assessments/{assessment['id']}/finish"
    )

    assert response.status_code == 409

    with TestSessionLocal() as db:
        assert db.get(Assessment, assessment["id"]).status == "in_progress"
