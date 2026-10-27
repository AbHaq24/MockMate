import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Base,
    Evaluation,
    Question,
    User,
)
from backend.db.session import get_db
from backend.main import app
from backend.services.analytics import get_user_analytics, get_user_weak_areas
from backend.services.retrieval import retriever


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


def register_and_login(client, email="analytics_user@example.com", password="SecurePassword123!"):
    client.post("/auth/register", json={"email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_completed_assessment_with_evaluation(
    db, user_id, topic, difficulty, score, feedback, strengths, improvements, version=1
):
    """Helper to seed an assessment, question, answer, and evaluation directly in DB."""
    from backend.api.assessments import question_hash

    q_text = f"Sample question on {topic} ({difficulty} v{version})?"
    q = Question(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        question_text=q_text,
        normalized_hash=question_hash(q_text),
        reference_answer=f"Sample reference answer for {topic}.",
    )
    db.add(q)
    db.flush()

    assessment = Assessment(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        questions_shown_count=1,
        status="completed",
    )
    db.add(assessment)
    db.flush()

    aq = AssessmentQuestion(
        assessment_id=assessment.id,
        question_id=q.id,
        display_number=1,
        version_number=version,
        is_current=True,
    )
    db.add(aq)
    db.flush()

    ans = Answer(
        assessment_question_id=aq.id,
        answer_text=f"My answer explaining {topic}.",
    )
    db.add(ans)
    db.flush()

    ev = Evaluation(
        answer_id=ans.id,
        score=score,
        feedback=feedback,
        strengths=strengths,
        improvements=improvements,
    )
    db.add(ev)
    db.commit()

    return assessment


# ===========================================================================
# 1. Analytics Service & Endpoint Tests
# ===========================================================================

def test_analytics_empty_history(client):
    headers = register_and_login(client, email="empty_user@example.com")
    res = client.get("/assessments/analytics", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["total_completed"] == 0
    assert data["total_evaluated"] == 0
    assert data["average_score"] == 0.0
    assert data["best_score"] == 0
    assert data["topic_performance"] == []
    assert data["strengths"] == []
    assert data["improvement_areas"] == []
    assert data["weak_topics"] == []


def test_analytics_score_aggregation_and_topic_grouping(client):
    headers = register_and_login(client, email="student@example.com")

    with TestSessionLocal() as db:
        user = db.query(User).filter_by(email="student@example.com").first()

        # Seed 2 Python evaluations (scores: 80, 90) -> avg 85 (Strength)
        create_completed_assessment_with_evaluation(
            db, user.id, "Python", "Medium", 80,
            feedback="Good answer",
            strengths="Clear explanation of generators and yield statements.",
            improvements="Add more detail on memory profiling.",
        )
        create_completed_assessment_with_evaluation(
            db, user.id, "Python", "Hard", 90,
            feedback="Excellent depth",
            strengths="Mastery of GIL mechanics and multiprocessing bypass.",
            improvements="None noted.",
        )

        # Seed 1 SQL evaluation (score: 55) -> avg 55 (Weakness)
        create_completed_assessment_with_evaluation(
            db, user.id, "SQL", "Medium", 55,
            feedback="Significant gaps",
            strengths="Understood basic JOIN semantics.",
            improvements="Review window functions and DENSE_RANK partition clauses.",
        )

    res = client.get("/assessments/analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_completed"] == 3
    assert data["total_evaluated"] == 3
    assert data["average_score"] == 75.0
    assert data["best_score"] == 90

    # Topic breakdown
    topics = {tp["topic"]: tp for tp in data["topic_performance"]}
    assert "Python" in topics
    assert "SQL" in topics

    assert topics["Python"]["attempts"] == 2
    assert topics["Python"]["average_score"] == 85.0
    assert topics["Python"]["best_score"] == 90

    assert topics["SQL"]["attempts"] == 1
    assert topics["SQL"]["average_score"] == 55.0
    assert topics["SQL"]["best_score"] == 55

    # Check identified strengths and weak topics
    assert "Python" in str(data["strengths"])
    assert "SQL" in data["weak_topics"]
    assert any("window functions" in imp.lower() for imp in data["improvement_areas"])


def test_analytics_user_data_isolation(client):
    headers_a = register_and_login(client, email="user_a@example.com")
    headers_b = register_and_login(client, email="user_b@example.com")

    with TestSessionLocal() as db:
        user_a = db.query(User).filter_by(email="user_a@example.com").first()
        create_completed_assessment_with_evaluation(
            db, user_a.id, "Machine Learning", "Easy", 95,
            feedback="Flawless", strengths="Strong basics", improvements="None",
        )

    # User A should see 1 completed evaluation
    res_a = client.get("/assessments/analytics", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["total_evaluated"] == 1
    assert res_a.json()["best_score"] == 95

    # User B must have completely empty analytics (Strict Isolation)
    res_b = client.get("/assessments/analytics", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["total_evaluated"] == 0
    assert res_b.json()["topic_performance"] == []

    # User B must also have an empty assessment history
    history_b = client.get("/assessments", headers=headers_b)
    assert history_b.status_code == 200
    assert len(history_b.json()) == 0


# ===========================================================================
# 2. Enhanced Assessment History Tests
# ===========================================================================

def test_assessment_history_includes_full_review_details(client):
    headers = register_and_login(client, email="reviewer@example.com")

    with TestSessionLocal() as db:
        user = db.query(User).filter_by(email="reviewer@example.com").first()
        create_completed_assessment_with_evaluation(
            db, user.id, "Deep Learning", "Medium", 88,
            feedback="Very detailed transformer analysis.",
            strengths="Accurately derived Query-Key-Value attention dot products.",
            improvements="Mention temperature scaling in decoding.",
        )

    res = client.get("/assessments", headers=headers)
    assert res.status_code == 200
    history = res.json()
    assert len(history) == 1

    item = history[0]
    assert item["topic"] == "Deep Learning"
    assert item["difficulty"] == "Medium"
    assert item["status"] == "completed"
    assert item["score"] == 88
    assert item["feedback"] == "Very detailed transformer analysis."
    assert "Query-Key-Value" in item["strengths"]
    assert "temperature scaling" in item["improvements"]
    assert "Deep Learning" in item["question"]
    assert item["answer"] is not None
    assert item["display_number"] == 1
    assert item["version_number"] == 1


def test_assessment_history_selects_correct_version_when_regenerated(client):
    """When a question slot has been regenerated, history should link to the

    exact answered question version.
    """
    headers = register_and_login(client, email="version_user@example.com")
    from backend.api.assessments import question_hash

    with TestSessionLocal() as db:
        user = db.query(User).filter_by(email="version_user@example.com").first()

        assessment = Assessment(
            user_id=user.id,
            topic="Python",
            difficulty="Easy",
            questions_shown_count=1,
            status="completed",
        )
        db.add(assessment)
        db.flush()

        # Question v1 (unanswered, skipped)
        q1 = Question(
            user_id=user.id, topic="Python", difficulty="Easy",
            question_text="Old Question Version 1?", normalized_hash=question_hash("Old Question Version 1?"),
            reference_answer="Old Answer 1",
        )
        db.add(q1)
        db.flush()

        aq1 = AssessmentQuestion(
            assessment_id=assessment.id, question_id=q1.id,
            display_number=1, version_number=1, is_current=False,
        )
        db.add(aq1)

        # Question v2 (regenerated and answered)
        q2 = Question(
            user_id=user.id, topic="Python", difficulty="Easy",
            question_text="New Regenerated Question Version 2?", normalized_hash=question_hash("New Regenerated Question Version 2?"),
            reference_answer="New Answer 2",
        )
        db.add(q2)
        db.flush()

        aq2 = AssessmentQuestion(
            assessment_id=assessment.id, question_id=q2.id,
            display_number=1, version_number=2, is_current=True,
        )
        db.add(aq2)
        db.flush()

        # Answer attached to aq2
        ans = Answer(assessment_question_id=aq2.id, answer_text="Answer to Version 2.")
        db.add(ans)
        db.flush()

        ev = Evaluation(
            answer_id=ans.id, score=92, feedback="Great!",
            strengths="Good point", improvements="None",
        )
        db.add(ev)
        db.commit()

    res = client.get("/assessments", headers=headers)
    assert res.status_code == 200
    item = res.json()[0]

    assert item["version_number"] == 2
    assert "Version 2" in item["question"]
    assert item["answer"] == "Answer to Version 2."
    assert item["score"] == 92


def test_history_handles_assessment_finished_without_answer(client):
    headers = register_and_login(client, email="unfinished@example.com")
    from backend.api.assessments import question_hash

    with TestSessionLocal() as db:
        user = db.query(User).filter_by(email="unfinished@example.com").first()

        assessment = Assessment(
            user_id=user.id,
            topic="Statistics",
            difficulty="Hard",
            questions_shown_count=3,
            status="completed",
        )
        db.add(assessment)
        db.flush()

        q = Question(
            user_id=user.id, topic="Statistics", difficulty="Hard",
            question_text="Simpson Paradox question?", normalized_hash=question_hash("Simpson Paradox question?"),
            reference_answer="Reference on confounders",
        )
        db.add(q)
        db.flush()

        aq = AssessmentQuestion(
            assessment_id=assessment.id, question_id=q.id,
            display_number=3, version_number=1, is_current=True,
        )
        db.add(aq)
        db.commit()

    res = client.get("/assessments", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["score"] is None
    assert data[0]["answer"] is None
    assert "Simpson Paradox" in data[0]["question"]


# ===========================================================================
# 3. Personalization & Weakness Targeting Tests
# ===========================================================================

def test_get_user_weak_areas_insufficient_data(client):
    with TestSessionLocal() as db:
        # User with no history
        weaknesses = get_user_weak_areas(99999, db)
        assert weaknesses == []


def test_get_user_weak_areas_identifies_struggling_topics(client):
    with TestSessionLocal() as db:
        user = User(email="weakness_test@example.com", password_hash="hash", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Add low scoring SQL assessment
        create_completed_assessment_with_evaluation(
            db, user.id, "SQL", "Medium", 40,
            feedback="Needs work", strengths="Basic SELECT", improvements="Practice indexing and execution plans",
        )

        weak_areas = get_user_weak_areas(user.id, db)
        assert len(weak_areas) > 0
        assert "SQL" in weak_areas or any("indexing" in w.lower() for w in weak_areas)


def test_retriever_supports_personalized_focus_terms():
    # Regular retrieval without focus terms returns default top question
    default_res = retriever.retrieve_question("Python", "Medium")
    assert default_res is not None

    # Personalized retrieval focusing on decorators
    focused_res = retriever.retrieve_question(
        "Python", "Medium", focus_terms=["decorators", "wrapper"]
    )
    assert focused_res is not None
    assert "decorator" in focused_res["question"].lower()


def test_personalized_generation_passes_weakness_context_to_generator(client, monkeypatch):
    headers = register_and_login(client, email="adaptive_student@example.com")

    # 1. Seed past low-scoring evaluation in SQL
    with TestSessionLocal() as db:
        user = db.query(User).filter_by(email="adaptive_student@example.com").first()
        create_completed_assessment_with_evaluation(
            db, user.id, "SQL", "Hard", 45,
            feedback="Struggled", strengths="Understood tables", improvements="Review deadlock prevention and isolation levels",
        )

    # 2. Mock generate_question to verify focus_areas keyword argument is received
    captured_kwargs = {}

    def mock_adaptive_generator(topic, difficulty, previous_questions=None, focus_areas=None):
        captured_kwargs["topic"] = topic
        captured_kwargs["difficulty"] = difficulty
        captured_kwargs["focus_areas"] = focus_areas
        return {
            "question": "What isolation level prevents non-repeatable reads in PostgreSQL?",
            "reference_answer": "Repeatable Read or Serializable.",
        }

    monkeypatch.setattr("backend.api.assessments.generate_question", mock_adaptive_generator)

    # 3. Create a new assessment on SQL
    create_res = client.post("/assessments", json={"topic": "SQL", "difficulty": "Hard"}, headers=headers)
    assessment_id = create_res.json()["id"]

    # 4. Request question generation
    gen_res = client.post(f"/assessments/{assessment_id}/questions", headers=headers)
    assert gen_res.status_code == 200

    # 5. Verify captured focus_areas includes the user's past weakness
    assert captured_kwargs.get("focus_areas") is not None
    assert any("SQL" in fa or "deadlock" in fa.lower() for fa in captured_kwargs["focus_areas"])
