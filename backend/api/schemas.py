from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# -------------------------
# Authentication schemas
# -------------------------

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool


# -------------------------
# Assessment schemas
# -------------------------

class AssessmentCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=100)
    difficulty: Literal["Easy", "Medium", "Hard"]


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic: str
    difficulty: str
    questions_shown_count: int
    status: str


class AnswerSubmit(BaseModel):
    answer_text: str = Field(min_length=1, max_length=10000)


class EvaluationResponse(BaseModel):
    answer_id: int
    assessment_question_id: int
    score: int = Field(ge=0, le=100)
    feedback: str
    strengths: str
    improvements: str


class AssessmentHistoryItem(BaseModel):
    assessment_id: int
    topic: str
    difficulty: str
    status: str
    created_at: Optional[str] = None
    questions_shown_count: int = 0
    display_number: Optional[int] = None
    version_number: Optional[int] = None
    question: Optional[str] = None
    reference_answer: Optional[str] = None
    answer: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None


# -------------------------
# Analytics schemas
# -------------------------

class TopicPerformance(BaseModel):
    topic: str
    attempts: int
    average_score: float
    best_score: int


class AnalyticsResponse(BaseModel):
    total_completed: int
    total_evaluated: int
    average_score: float
    best_score: int
    topic_performance: list[TopicPerformance]
    strengths: list[str]
    improvement_areas: list[str]
    weak_topics: list[str]
