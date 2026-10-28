import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base, User, Assessment, AssessmentQuestion, Question, Answer, Evaluation
from backend.db.session import get_db
from backend.main import app
from backend.prompts import (
    evaluation_system_prompt,
    evaluation_user_prompt,
    question_system_prompt,
    question_user_prompt,
)
from backend.services.analytics import get_user_weak_areas
from backend.services.guardrails import (
    is_sql_or_db_topic,
    validate_question_topic_consistency,
    validate_reference_answer_completeness,
)
from backend.services.retrieval import (
    CURATED_QUESTION_BANK,
    is_topic_compatible,
    retriever,
)


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


def register_and_login(client: TestClient, email: str = "tester@example.com") -> dict:
    client.post(
        "/auth/register",
        json={"email": email, "password": "TestPassword123!"},
    )
    res = client.post(
        "/auth/login",
        json={"email": email, "password": "TestPassword123!"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Guardrails: SQL Topic Consistency Tests
# ===========================================================================

def test_is_sql_or_db_topic():
    assert is_sql_or_db_topic("SQL") is True
    assert is_sql_or_db_topic("SQL & Databases") is True
    assert is_sql_or_db_topic("PostgreSQL") is True
    assert is_sql_or_db_topic("Relational Database Design") is True
    # Explicit ML intent should NOT be treated as pure SQL
    assert is_sql_or_db_topic("SQL for Machine Learning") is False
    assert is_sql_or_db_topic("Machine Learning") is False
    assert is_sql_or_db_topic("Python") is False


def test_sql_question_consistency_guardrail_pure_sql():
    valid_sql_questions = [
        "What is the difference between WHERE and HAVING clauses in SQL?",
        "Explain the difference between ROW_NUMBER(), RANK(), and DENSE_RANK().",
        "How do B-Tree indexes improve query performance in PostgreSQL, and what are their trade-offs?",
        "Explain the four ACID properties in relational database transactions.",
        "Write a SQL query using GROUP BY and HAVING to find customers with more than 5 orders.",
    ]
    for q in valid_sql_questions:
        is_valid, reason = validate_question_topic_consistency("SQL", q)
        assert is_valid is True, f"Expected valid question: {reason}"

        # Should also be valid for SQL & Databases
        is_valid, reason = validate_question_topic_consistency("SQL & Databases", q)
        assert is_valid is True, f"Expected valid question: {reason}"


def test_sql_question_consistency_guardrail_rejects_ml_bleed():
    # Exactly replicating the problem described in user prompt
    mixed_questions = [
        "Write a SQL query to calculate Mean Squared Error (MSE) and explain the bias-variance decomposition.",
        "How does model complexity and optimal complexity affect query execution in a relational database?",
        "Explain how overfitting in a neural network affects database indexing.",
        "Write a query to perform gradient descent optimization over a database table.",
        "What is the difference between an INNER JOIN and a random forest classifier?",
    ]
    for q in mixed_questions:
        is_valid, reason = validate_question_topic_consistency("SQL", q)
        assert is_valid is False
        assert "Mixed topic detected" in reason

        is_valid, reason = validate_question_topic_consistency("SQL & Databases", q)
        assert is_valid is False
        assert "Mixed topic detected" in reason


# ===========================================================================
# 2. Guardrails: Reference Answer Completeness Tests
# ===========================================================================

def test_reference_answer_completeness_guardrail_valid():
    question = "Write an SQL query to retrieve the second highest salary and explain how the OFFSET clause works."
    reference_answer = (
        "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1; "
        "The OFFSET clause skips the specified number of rows (here 1) before beginning to return "
        "rows from the query result set, allowing pagination or rank-based row extraction."
    )
    is_complete, reason = validate_reference_answer_completeness(question, reference_answer)
    assert is_complete is True
    assert reason is None


def test_reference_answer_completeness_guardrail_rejects_too_brief():
    question = "Explain the difference between WHERE and HAVING in SQL."
    reference_answer = "Too short."
    is_complete, reason = validate_reference_answer_completeness(question, reference_answer)
    assert is_complete is False
    assert "too brief" in reason


def test_reference_answer_completeness_guardrail_rejects_missing_query():
    question = "Write an SQL query to find duplicate emails in a table and describe the reasoning."
    # Explains the concept but completely omits the requested SQL query
    reference_answer = (
        "To find duplicate emails, one should group the records by the email address "
        "and count how many times each address appears in the dataset."
    )
    is_complete, reason = validate_reference_answer_completeness(question, reference_answer)
    assert is_complete is False
    assert "lacks SQL query syntax" in reason


# ===========================================================================
# 3. Retrieval Engine: Topic Compatibility & Isolation Tests
# ===========================================================================

def test_is_topic_compatible():
    assert is_topic_compatible("SQL", "SQL") is True
    assert is_topic_compatible("SQL", "SQL & Databases") is True
    assert is_topic_compatible("SQL", "PostgreSQL Queries") is True
    assert is_topic_compatible("Machine Learning", "SQL") is False
    assert is_topic_compatible("Python", "SQL") is False
    assert is_topic_compatible("Deep Learning & GenAI", "SQL") is False
    assert is_topic_compatible("Statistics", "SQL") is False

    assert is_topic_compatible("Machine Learning", "Machine Learning") is True
    assert is_topic_compatible("Deep Learning & GenAI", "Deep Learning") is True
    assert is_topic_compatible("Python", "Python 3.12") is True
    assert is_topic_compatible("SQL", "Knitting sweaters") is False


def test_retriever_filters_by_topic_and_prevents_ml_in_sql():
    # 1. Topic-appropriate focus terms return the relevant SQL question
    sql_res = retriever.retrieve_question("SQL", "Easy", focus_terms=["having", "where"])
    assert sql_res is not None
    assert "where" in sql_res["question"].lower()

    # 2. Unrelated ML focus terms NEVER cause an ML question to be returned for an SQL topic
    ml_focus_terms = ["bias-variance", "loss function", "model complexity", "overfitting"]
    ml_leak_res = retriever.retrieve_question("SQL", "Easy", focus_terms=ml_focus_terms)
    if ml_leak_res is not None:
        clean_q = ml_leak_res["question"].lower()
        assert "bias" not in clean_q
        assert "variance" not in clean_q
        assert "loss" not in clean_q
        assert "overfitting" not in clean_q


def test_curated_bank_sql_questions_have_valid_consistency_and_completeness():
    sql_questions = [q for q in CURATED_QUESTION_BANK if q.topic == "SQL"]
    assert len(sql_questions) >= 5

    for q in sql_questions:
        is_consistent, reason = validate_question_topic_consistency("SQL", q.question)
        assert is_consistent is True, f"Inconsistent SQL question: {q.question} ({reason})"

        is_complete, reason = validate_reference_answer_completeness(q.question, q.reference_answer)
        assert is_complete is True, f"Incomplete reference answer for: {q.question} ({reason})"


# ===========================================================================
# 4. Analytics & Personalization: Scoped Weakness Identification
# ===========================================================================

def test_analytics_weak_areas_topic_scoped(client):
    with TestSessionLocal() as db:
        user = User(email="scoped_weakness@example.com", password_hash="hash", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Seed low score in Machine Learning (avg 40)
        asmt_ml = Assessment(user_id=user.id, topic="Machine Learning", difficulty="Medium", status="completed", questions_shown_count=1)
        db.add(asmt_ml)
        db.commit()
        db.refresh(asmt_ml)

        q_ml = Question(user_id=user.id, topic="Machine Learning", difficulty="Medium", question_text="Explain bias variance.", normalized_hash="ml1", reference_answer="Bias variance tradeoff.")
        db.add(q_ml)
        db.commit()
        db.refresh(q_ml)

        aq_ml = AssessmentQuestion(assessment_id=asmt_ml.id, question_id=q_ml.id, display_number=1, version_number=1, is_current=True)
        db.add(aq_ml)
        db.commit()
        db.refresh(aq_ml)

        ans_ml = Answer(assessment_question_id=aq_ml.id, answer_text="Not sure.")
        db.add(ans_ml)
        db.commit()
        db.refresh(ans_ml)

        eval_ml = Evaluation(answer_id=ans_ml.id, score=40, feedback="Poor", strengths="None", improvements="Study bias-variance decomposition and model complexity.")
        db.add(eval_ml)

        # Seed high score in SQL (avg 90)
        asmt_sql = Assessment(user_id=user.id, topic="SQL", difficulty="Easy", status="completed", questions_shown_count=1)
        db.add(asmt_sql)
        db.commit()
        db.refresh(asmt_sql)

        q_sql = Question(user_id=user.id, topic="SQL", difficulty="Easy", question_text="Explain WHERE vs HAVING.", normalized_hash="sql1", reference_answer="WHERE vs HAVING.")
        db.add(q_sql)
        db.commit()
        db.refresh(q_sql)

        aq_sql = AssessmentQuestion(assessment_id=asmt_sql.id, question_id=q_sql.id, display_number=1, version_number=1, is_current=True)
        db.add(aq_sql)
        db.commit()
        db.refresh(aq_sql)

        ans_sql = Answer(assessment_question_id=aq_sql.id, answer_text="WHERE filters rows, HAVING filters groups.")
        db.add(ans_sql)
        db.commit()
        db.refresh(ans_sql)

        eval_sql = Evaluation(answer_id=ans_sql.id, score=90, feedback="Great", strengths="Excellent understanding of aggregate filtering.", improvements="None")
        db.add(eval_sql)
        db.commit()

        # 1. When querying weak areas for SQL: MUST be empty because the user scored 90 in SQL
        sql_weaknesses = get_user_weak_areas(user.id, db, current_topic="SQL")
        assert sql_weaknesses == [], f"Expected empty weak areas for SQL, got: {sql_weaknesses}"

        # 2. When querying weak areas for Machine Learning: MUST include ML weaknesses
        ml_weaknesses = get_user_weak_areas(user.id, db, current_topic="Machine Learning")
        assert len(ml_weaknesses) > 0
        assert any("bias" in w.lower() or "Machine Learning" in w for w in ml_weaknesses)


# ===========================================================================
# 5. API: Mixed-Topic Question Rejection & Automatic Regeneration Tests
# ===========================================================================

def test_api_question_generation_rejects_mixed_topic_and_regenerates(client, monkeypatch):
    headers = register_and_login(client, email="regenerate_mixed@example.com")

    # Create an assessment on SQL
    create_res = client.post("/assessments", json={"topic": "SQL", "difficulty": "Easy"}, headers=headers)
    assert create_res.status_code == 201
    assessment_id = create_res.json()["id"]

    call_count = 0

    def mock_generator_with_mixed_first_attempt(topic, difficulty, previous_questions=None, focus_areas=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Attempt 1: Mixed SQL + ML theory question (must be rejected!)
            return {
                "question": "Write an SQL query to calculate Mean Squared Error (MSE) and explain the bias-variance decomposition.",
                "reference_answer": "SELECT AVG(POW(y_true - y_pred, 2)) FROM predictions; Bias-variance tradeoff details.",
            }
        # Attempt 2: Pure SQL question (must be accepted!)
        return {
            "question": "What is the difference between WHERE and HAVING clauses in SQL, and when must you use HAVING?",
            "reference_answer": "WHERE filters individual rows before grouping; HAVING filters aggregated groups.",
        }

    monkeypatch.setattr("backend.api.assessments.generate_question", mock_generator_with_mixed_first_attempt)

    gen_res = client.post(f"/assessments/{assessment_id}/questions", headers=headers)
    assert gen_res.status_code == 200

    data = gen_res.json()
    # Verify attempt 1 was rejected and attempt 2 was saved
    assert call_count == 2
    assert "bias-variance" not in data["question"].lower()
    assert "where" in data["question"].lower() or "having" in data["question"].lower()


def test_api_question_generation_rejects_incomplete_reference_answer_and_regenerates(client, monkeypatch):
    headers = register_and_login(client, email="regenerate_incomplete@example.com")

    create_res = client.post("/assessments", json={"topic": "SQL", "difficulty": "Medium"}, headers=headers)
    assert create_res.status_code == 201
    assessment_id = create_res.json()["id"]

    call_count = 0

    def mock_generator_with_incomplete_ref(topic, difficulty, previous_questions=None, focus_areas=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Attempt 1: Asks for query and explanation, but reference answer completely omits the explanation
            return {
                "question": "Write an SQL query to retrieve all active users and explain how the WHERE clause filters rows.",
                "reference_answer": "SELECT * FROM users WHERE active = true;",
            }
        # Attempt 2: Complete reference answer containing both query and full explanation
        return {
            "question": "Write an SQL query to retrieve all active users and explain how the WHERE clause filters rows.",
            "reference_answer": (
                "SELECT * FROM users WHERE active = true; "
                "The WHERE clause filters individual rows before aggregation by evaluating the boolean predicate for each row."
            ),
        }

    monkeypatch.setattr("backend.api.assessments.generate_question", mock_generator_with_incomplete_ref)

    gen_res = client.post(f"/assessments/{assessment_id}/questions", headers=headers)
    assert gen_res.status_code == 200

    data = gen_res.json()
    assert call_count == 2
    assert data["question"] is not None


# ===========================================================================
# 6. Evaluation Prompts & Fair Partial Credit Verification
# ===========================================================================

def test_prompts_contain_strict_topic_isolation_and_fair_partial_credit():
    sys_prompt = question_system_prompt()
    assert "Strict Topic Isolation" in sys_prompt
    assert "SQL" in sys_prompt
    assert "DO NOT introduce unrelated Machine Learning concepts" in sys_prompt
    assert "Reference Answer Completeness" in sys_prompt

    eval_sys = evaluation_system_prompt()
    assert "Evaluate Against Full Question & Reference Answer" in eval_sys
    assert "Fair Partial Credit" in eval_sys
    assert "65-75" in eval_sys
    assert "strengths" in eval_sys
    assert "improvements" in eval_sys

    eval_user = evaluation_user_prompt(
        topic="SQL",
        difficulty="Easy",
        question="Write an SQL query to retrieve all employees with salary > 50000 and explain how WHERE filters rows.",
        reference_answer="SELECT * FROM employees WHERE salary > 50000; WHERE evaluates conditions per row before aggregation.",
        answer="SELECT * FROM employees WHERE salary > 50000;",
    )
    assert "fair partial credit" in eval_user.lower()
    assert "65-75%" in eval_user
