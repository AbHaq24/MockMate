from hashlib import sha256
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.auth import get_current_user
from backend.api.schemas import AssessmentCreate, AssessmentResponse
from backend.db.models import Assessment, AssessmentQuestion, Question, User
from backend.db.session import get_db
from backend.llm import generate_question

router = APIRouter(prefix="/assessments", tags=["Assessments"])

MAX_QUESTIONS = 3
MAX_GENERATION_ATTEMPTS = 3


def normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def question_hash(text: str) -> str:
    return sha256(normalize_question(text).encode("utf-8")).hexdigest()


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
    topic = data.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Topic cannot be blank.")

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
def generate_assessment_question(
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
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if assessment.status != "in_progress":
        raise HTTPException(status_code=409, detail="Assessment is not active.")

    if assessment.questions_shown_count >= MAX_QUESTIONS:
        raise HTTPException(
            status_code=409,
            detail="The three-question limit has been reached.",
        )

    previous_questions = db.scalars(
        select(Question.question_text).where(
            Question.user_id == current_user.id
        )
    ).all()

    known_hashes = {
        question_hash(text) for text in previous_questions
    }

    for _ in range(MAX_GENERATION_ATTEMPTS):
        try:
            generated = generate_question(
                assessment.topic,
                assessment.difficulty,
                previous_questions=previous_questions,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        text = generated["question"]
        digest = question_hash(text)

        if digest in known_hashes:
            continue

        question = Question(
            user_id=current_user.id,
            topic=assessment.topic,
            difficulty=assessment.difficulty,
            question_text=text,
            normalized_hash=digest,
            reference_answer=generated["reference_answer"],
        )

        try:
            db.add(question)
            db.flush()

            display_number = assessment.questions_shown_count + 1
            assessment_question = AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=question.id,
                display_number=display_number,
            )
            db.add(assessment_question)

            assessment.questions_shown_count += 1
            db.commit()
            db.refresh(assessment_question)

            return {
                "assessment_id": assessment.id,
                "assessment_question_id": assessment_question.id,
                "question_id": question.id,
                "display_number": display_number,
                "question": question.question_text,
            }
        except IntegrityError:
            db.rollback()
            assessment = db.scalar(
                select(Assessment).where(
                    Assessment.id == assessment_id,
                    Assessment.user_id == current_user.id,
                )
            )
            if assessment is None or assessment.questions_shown_count >= MAX_QUESTIONS:
                raise HTTPException(
                    status_code=409,
                    detail="The assessment has reached its question limit.",
                )
            known_hashes.add(digest)

    raise HTTPException(
        status_code=502,
        detail="Could not generate a new question. Please try again.",
    )

