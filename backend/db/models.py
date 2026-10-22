
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="user"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="user"
    )


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint(
            "questions_shown_count >= 0 AND questions_shown_count <= 3",
            name="ck_assessments_questions_shown_count",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed')",
            name="ck_assessments_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    questions_shown_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="in_progress", server_default="in_progress",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="assessments")
    assessment_questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "difficulty IN ('Easy', 'Medium', 'Hard')",
            name="ck_questions_difficulty",
        ),
        UniqueConstraint(
            "user_id", "normalized_hash",
            name="uq_questions_user_normalized_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="questions")
    assessment_questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="question"
    )



class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "display_number",
            "version_number",
            name="uq_assessment_question_slot_version",
        ),
        UniqueConstraint(
            "assessment_id",
            "question_id",
            name="uq_assessment_questions_question",
        ),
        CheckConstraint(
            "display_number BETWEEN 1 AND 3",
            name="ck_assessment_questions_display_number",
        ),
        CheckConstraint(
            "version_number BETWEEN 1 AND 3",
            name="ck_assessment_question_version_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="RESTRICT"), index=True
    )
    display_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_number: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    displayed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assessment: Mapped["Assessment"] = relationship(
        back_populates="assessment_questions"
    )
    question: Mapped["Question"] = relationship(
        back_populates="assessment_questions"
    )
    answer: Mapped["Answer | None"] = relationship(
        back_populates="assessment_question",
        cascade="all, delete-orphan",
        uselist=False,
    )



class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    assessment_question_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assessment_question: Mapped["AssessmentQuestion"] = relationship(
        back_populates="answer"
    )
    evaluation: Mapped["Evaluation | None"] = relationship(
        back_populates="answer",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_evaluations_score",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    answer_id: Mapped[int] = mapped_column(
        ForeignKey("answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[str] = mapped_column(Text, nullable=False)
    improvements: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    answer: Mapped["Answer"] = relationship(back_populates="evaluation")
