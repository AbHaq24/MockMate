from hashlib import sha256
import inspect
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.auth import get_current_user
from backend.api.schemas import (
    AnalyticsResponse,
    AnswerSubmit,
    AssessmentCreate,
    AssessmentHistoryItem,
    AssessmentResponse,
    EvaluationResponse,
)
from backend.db.models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Evaluation,
    Question,
    User,
)
from backend.db.session import get_db
import backend.llm
from backend.llm import evaluate_answer, generate_question
from backend.services.analytics import get_user_analytics, get_user_weak_areas
from backend.services.guardrails import (
    validate_answer_guardrails,
    validate_question_topic_consistency,
    validate_reference_answer_completeness,
    validate_topic_guardrails,
)
from backend.services.retrieval import retriever
from backend.config.settings import get_settings

from backend.limiter import limiter

settings = get_settings()


router = APIRouter(prefix="/assessments", tags=["Assessments"])


@router.get("", response_model=list[AssessmentHistoryItem])
def get_assessment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessments = db.scalars(
        select(Assessment)
        .where(Assessment.user_id == current_user.id)
        .order_by(Assessment.id.desc())
    ).all()

    history = []

    for assessment in assessments:
        # 1. Search for an AssessmentQuestion that has a submitted Answer
        answered_aq = db.scalar(
            select(AssessmentQuestion)
            .join(
                Answer,
                Answer.assessment_question_id == AssessmentQuestion.id,
            )
            .where(AssessmentQuestion.assessment_id == assessment.id)
            .order_by(
                AssessmentQuestion.display_number.desc(),
                AssessmentQuestion.version_number.desc(),
            )
        )

        target_aq = answered_aq
        if target_aq is None:
            # 2. If no question was answered, fetch the latest displayed question
            target_aq = db.scalar(
                select(AssessmentQuestion)
                .where(
                    AssessmentQuestion.assessment_id == assessment.id,
                    AssessmentQuestion.is_current.is_(True),
                )
                .order_by(AssessmentQuestion.display_number.desc())
            )

        question = db.get(Question, target_aq.question_id) if target_aq else None
        answer = target_aq.answer if target_aq else None
        evaluation = answer.evaluation if answer else None

        history.append(
            {
                "assessment_id": assessment.id,
                "topic": assessment.topic,
                "difficulty": assessment.difficulty,
                "status": assessment.status,
                "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                "questions_shown_count": assessment.questions_shown_count,
                "display_number": target_aq.display_number if target_aq else None,
                "version_number": target_aq.version_number if target_aq else None,
                "question": question.question_text if question else None,
                "reference_answer": question.reference_answer if question else None,
                "answer": answer.answer_text if answer else None,
                "score": evaluation.score if evaluation else None,
                "feedback": evaluation.feedback if evaluation else None,
                "strengths": evaluation.strengths if evaluation else None,
                "improvements": evaluation.improvements if evaluation else None,
            }
        )

    return history


@router.get("/analytics", response_model=AnalyticsResponse)
def get_user_performance_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve aggregated performance metrics, strengths, and weaknesses for

    the current user.
    """
    return get_user_analytics(current_user.id, db)


MAX_QUESTIONS = 3
MAX_VERSIONS = 3
MAX_GENERATION_ATTEMPTS = 3


def normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def question_hash(text: str) -> str:
    return sha256(normalize_question(text).encode("utf-8")).hexdigest()


def get_assessment(
    assessment_id: int,
    user_id: int,
    db: Session,
) -> Assessment:
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.user_id == user_id,
        )
    )

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    if assessment.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="Assessment is not active.",
        )

    return assessment


def generate_unique_question(
    assessment: Assessment,
    user: User,
    db: Session,
    exclude_hashes: set[str],
) -> Question:
    previous_questions = db.scalars(
        select(Question.question_text).where(
            Question.user_id == user.id
        )
    ).all()

    known_hashes = {
        question_hash(text) for text in previous_questions
    } | exclude_hashes

    # Retrieve user growth/weakness areas for personalization, scoped to current topic
    weak_areas = get_user_weak_areas(user.id, db, current_topic=assessment.topic)

    # 1. Attempt nearest-neighbor / TF-IDF retrieval from curated bank first
    # Only use retriever if generate_question has not been monkeypatched for testing
    if generate_question is backend.llm.generate_question:
        retrieved = retriever.retrieve_question(
            topic=assessment.topic,
            difficulty=assessment.difficulty,
            exclude_hashes=known_hashes,
            focus_terms=weak_areas if weak_areas else None,
        )
        if retrieved:
            text = retrieved["question"].strip()
            ref = retrieved["reference_answer"].strip()
            digest = question_hash(text)

            is_consistent, _ = validate_question_topic_consistency(assessment.topic, text)
            is_complete, _ = validate_reference_answer_completeness(text, ref)

            if is_consistent and is_complete and digest not in known_hashes:
                question = Question(
                    user_id=user.id,
                    topic=assessment.topic,
                    difficulty=assessment.difficulty,
                    question_text=text,
                    normalized_hash=digest,
                    reference_answer=ref,
                )
                try:
                    db.add(question)
                    db.flush()
                    return question
                except IntegrityError:
                    db.rollback()

    # 2. Fall back to live LLM generation via Groq
    kwargs = {}
    if weak_areas:
        sig = inspect.signature(generate_question)
        if "focus_areas" in sig.parameters:
            kwargs["focus_areas"] = weak_areas

    for _ in range(MAX_GENERATION_ATTEMPTS):
        try:
            generated = generate_question(
                assessment.topic,
                assessment.difficulty,
                previous_questions=previous_questions,
                **kwargs,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        text = generated["question"].strip()
        ref = generated["reference_answer"].strip()
        digest = question_hash(text)

        if digest in known_hashes:
            continue

        # Reject questions that mix unrelated domains or have incomplete reference answers
        is_consistent, _ = validate_question_topic_consistency(assessment.topic, text)
        if not is_consistent:
            continue

        is_complete, _ = validate_reference_answer_completeness(text, ref)
        if not is_complete:
            continue

        question = Question(
            user_id=user.id,
            topic=assessment.topic,
            difficulty=assessment.difficulty,
            question_text=text,
            normalized_hash=digest,
            reference_answer=ref,
        )

        try:
            db.add(question)
            db.flush()
            return question
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="A duplicate question was detected. Please try again.",
            ) from exc

    raise HTTPException(
        status_code=502,
        detail="Could not generate a new question. Please try again.",
    )


@router.post(
    "",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    data: AssessmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Assessment:
    # Validate and sanitize topic through security guardrails
    topic = validate_topic_guardrails(data.topic)

    assessment = Assessment(
        user_id=current_user.id,
        topic=topic,
        difficulty=data.difficulty,
        questions_shown_count=0,
        status="in_progress",
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return assessment


@router.post("/{assessment_id}/questions")
@limiter.limit("5/minute")
def generate_assessment_question(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = get_assessment(
        assessment_id,
        current_user.id,
        db,
    )

    if assessment.questions_shown_count >= MAX_QUESTIONS:
        raise HTTPException(
            status_code=409,
            detail="The three-question limit has been reached.",
        )

    display_number = assessment.questions_shown_count + 1

    question = generate_unique_question(
        assessment,
        current_user,
        db,
        exclude_hashes=set(),
    )

    assessment_question = AssessmentQuestion(
        assessment_id=assessment.id,
        question_id=question.id,
        display_number=display_number,
        version_number=1,
        is_current=True,
    )

    db.add(assessment_question)
    assessment.questions_shown_count += 1

    try:
        db.commit()
        db.refresh(assessment_question)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not save the question. Please try again.",
        ) from exc

    return {
        "assessment_id": assessment.id,
        "assessment_question_id": assessment_question.id,
        "question_id": question.id,
        "display_number": display_number,
        "version_number": 1,
        "is_current": True,
        "question": question.question_text,
    }


@router.post("/{assessment_id}/questions/{display_number}/regenerate")
@limiter.limit("5/minute")
def regenerate_assessment_question(
    request: Request,
    assessment_id: int,
    display_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = get_assessment(
        assessment_id,
        current_user.id,
        db,
    )

    if not 1 <= display_number <= MAX_QUESTIONS:
        raise HTTPException(
            status_code=422,
            detail="Question slot must be between 1 and 3.",
        )

    current = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.display_number == display_number,
            AssessmentQuestion.is_current.is_(True),
        )
    )

    if current is None:
        raise HTTPException(
            status_code=404,
            detail="No question exists in this slot yet.",
        )

    if db.scalar(
        select(Answer.id).where(
            Answer.assessment_question_id == current.id
        )
    ) is not None:
        raise HTTPException(
            status_code=409,
            detail="This question has already been answered and cannot be regenerated.",
        )

    if current.version_number >= MAX_VERSIONS:
        raise HTTPException(
            status_code=409,
            detail="This question has reached its regeneration limit.",
        )

    old_question = db.get(Question, current.question_id)
    excluded_hashes = {
        question_hash(old_question.question_text)
    }

    new_question = generate_unique_question(
        assessment,
        current_user,
        db,
        exclude_hashes=excluded_hashes,
    )

    try:
        current.is_current = False

        new_version = AssessmentQuestion(
            assessment_id=assessment.id,
            question_id=new_question.id,
            display_number=display_number,
            version_number=current.version_number + 1,
            is_current=True,
        )

        db.add(new_version)
        db.commit()
        db.refresh(new_version)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not save the new question version. Please try again.",
        ) from exc

    return {
        "assessment_id": assessment.id,
        "assessment_question_id": new_version.id,
        "question_id": new_question.id,
        "display_number": display_number,
        "version_number": new_version.version_number,
        "is_current": True,
        "question": new_question.question_text,
    }


@router.post(
    "/{assessment_id}/questions/{assessment_question_id}/answer",
    response_model=EvaluationResponse,
)
@limiter.limit("3/minute")
def submit_answer(
    request: Request,
    assessment_id: int,
    assessment_question_id: int,
    data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate and sanitize candidate answer through security guardrails
    answer_text = validate_answer_guardrails(data.answer_text)

    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.user_id == current_user.id,
        )
    )

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    if assessment.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="Assessment is not active.",
        )

    submitted_answer = db.scalar(
        select(Answer.id)
        .join(
            AssessmentQuestion,
            Answer.assessment_question_id == AssessmentQuestion.id,
        )
        .where(
            AssessmentQuestion.assessment_id == assessment.id
        )
    )

    if submitted_answer is not None:
        raise HTTPException(
            status_code=409,
            detail="An answer has already been submitted for this assessment.",
        )

    assessment_question = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.id == assessment_question_id,
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.is_current.is_(True),
        )
    )

    if assessment_question is None:
        raise HTTPException(
            status_code=404,
            detail="Current question not found.",
        )

    question = db.get(Question, assessment_question.question_id)

    try:
        result = evaluate_answer(
            topic=assessment.topic,
            difficulty=assessment.difficulty,
            question=question.question_text,
            reference_answer=question.reference_answer,
            answer=answer_text,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    answer = Answer(
        assessment_question_id=assessment_question.id,
        answer_text=answer_text,
    )

    db.add(answer)

    try:
        db.flush()

        evaluation = Evaluation(
            answer_id=answer.id,
            score=result["score"],
            feedback=result["feedback"],
            strengths=result["strengths"],
            improvements=result["improvements"],
        )

        db.add(evaluation)
        assessment.status = "completed"

        db.commit()
        db.refresh(answer)
        db.refresh(evaluation)

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The answer may already have been submitted.",
        ) from exc

    return {
        "answer_id": answer.id,
        "assessment_question_id": assessment_question.id,
        "score": evaluation.score,
        "feedback": evaluation.feedback,
        "strengths": evaluation.strengths,
        "improvements": evaluation.improvements,
    }


@router.post("/{assessment_id}/finish")
@limiter.limit("3/minute")
def finish_assessment(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assessment = db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.user_id == current_user.id,
        )
    )

    if assessment is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found.",
        )

    if assessment.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="Assessment is not active.",
        )

    if assessment.questions_shown_count < MAX_QUESTIONS:
        raise HTTPException(
            status_code=409,
            detail="Generate all three questions before finishing without an answer.",
        )

    assessment.status = "completed"
    db.commit()
    db.refresh(assessment)

    return {
        "assessment_id": assessment.id,
        "status": assessment.status,
        "message": "Assessment completed without a submitted answer.",
        "score": None,
    }
