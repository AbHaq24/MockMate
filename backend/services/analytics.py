from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Answer, Assessment, AssessmentQuestion, Evaluation, Question


def get_user_analytics(user_id: int, db: Session) -> dict[str, Any]:
    """Calculate aggregated performance analytics, strengths, and weaknesses

    for an authenticated user.
    """
    # 1. Total completed assessments
    completed_assessments = db.scalars(
        select(Assessment)
        .where(
            Assessment.user_id == user_id,
            Assessment.status == "completed",
        )
    ).all()
    total_completed = len(completed_assessments)

    # 2. Query all evaluations associated with this user's assessments
    # Join Assessment -> AssessmentQuestion -> Answer -> Evaluation
    records = db.execute(
        select(
            Assessment.id.label("assessment_id"),
            Assessment.topic.label("topic"),
            Assessment.difficulty.label("difficulty"),
            Question.question_text.label("question_text"),
            Answer.answer_text.label("answer_text"),
            Evaluation.score.label("score"),
            Evaluation.feedback.label("feedback"),
            Evaluation.strengths.label("strengths"),
            Evaluation.improvements.label("improvements"),
            Evaluation.created_at.label("evaluated_at"),
        )
        .join(AssessmentQuestion, AssessmentQuestion.assessment_id == Assessment.id)
        .join(Question, Question.id == AssessmentQuestion.question_id)
        .join(Answer, Answer.assessment_question_id == AssessmentQuestion.id)
        .join(Evaluation, Evaluation.answer_id == Answer.id)
        .where(Assessment.user_id == user_id)
        .order_by(Evaluation.created_at.desc())
    ).all()

    # Deduplicate by assessment_id so multiple versions do not skew statistics
    seen_assessments: set[int] = set()
    deduped_evaluations: list[Any] = []
    for r in records:
        if r.assessment_id not in seen_assessments:
            seen_assessments.add(r.assessment_id)
            deduped_evaluations.append(r)

    total_evaluated = len(deduped_evaluations)

    if total_evaluated == 0:
        return {
            "total_completed": total_completed,
            "total_evaluated": 0,
            "average_score": 0.0,
            "best_score": 0,
            "topic_performance": [],
            "strengths": [],
            "improvement_areas": [],
            "weak_topics": [],
        }

    # 3. Overall scores
    scores = [r.score for r in deduped_evaluations]
    average_score = round(sum(scores) / total_evaluated, 1)
    best_score = max(scores)

    # 4. Group by topic
    topic_data: dict[str, list[int]] = defaultdict(list)
    topic_strengths: dict[str, list[str]] = defaultdict(list)
    topic_improvements: dict[str, list[str]] = defaultdict(list)

    for r in deduped_evaluations:
        t = r.topic.strip()
        topic_data[t].append(r.score)
        if r.strengths and len(r.strengths.strip()) > 5:
            topic_strengths[t].append(r.strengths.strip())
        if r.improvements and len(r.improvements.strip()) > 5:
            topic_improvements[t].append(r.improvements.strip())

    topic_performance = []
    weak_topics: list[str] = []
    strong_topics: list[str] = []

    for topic, t_scores in topic_data.items():
        t_avg = round(sum(t_scores) / len(t_scores), 1)
        t_best = max(t_scores)
        topic_performance.append(
            {
                "topic": topic,
                "attempts": len(t_scores),
                "average_score": t_avg,
                "best_score": t_best,
            }
        )
        if t_avg >= 75:
            strong_topics.append(topic)
        elif t_avg < 70:
            weak_topics.append(topic)

    # Sort topic performance by average score descending
    topic_performance.sort(key=lambda x: x["average_score"], reverse=True)

    # 5. Extract structured strengths
    strengths_list: list[str] = []
    for topic in strong_topics:
        avg = next(tp["average_score"] for tp in topic_performance if tp["topic"] == topic)
        strengths_list.append(f"{topic}: Consistently high performance (average score {avg}%).")

    # Add specific strength excerpts from recent evaluations
    for r in deduped_evaluations:
        if r.score >= 70 and r.strengths:
            clean_str = r.strengths.strip()
            # Truncate clean sentence if long
            if clean_str and clean_str not in strengths_list and len(strengths_list) < 5:
                strengths_list.append(clean_str)

    # 6. Extract structured improvement areas
    improvement_list: list[str] = []
    for topic in weak_topics:
        avg = next(tp["average_score"] for tp in topic_performance if tp["topic"] == topic)
        improvement_list.append(f"{topic}: Recommended focus area (average score {avg}%).")

    # Add specific improvement suggestions from evaluation data
    for r in deduped_evaluations:
        if r.improvements:
            clean_imp = r.improvements.strip()
            if clean_imp and clean_imp not in improvement_list and len(improvement_list) < 5:
                improvement_list.append(clean_imp)

    return {
        "total_completed": total_completed,
        "total_evaluated": total_evaluated,
        "average_score": average_score,
        "best_score": best_score,
        "topic_performance": topic_performance,
        "strengths": strengths_list,
        "improvement_areas": improvement_list,
        "weak_topics": weak_topics,
    }


def get_user_weak_areas(user_id: int, db: Session) -> list[str]:
    """Retrieve recurring weak areas and topics for adaptive personalization.

    Returns an empty list if there is insufficient historical evaluation data.
    """
    analytics = get_user_analytics(user_id, db)
    if analytics["total_evaluated"] == 0:
        return []

    weaknesses = []
    if analytics["weak_topics"]:
        weaknesses.extend(analytics["weak_topics"])

    # Include specific improvement points if available
    for item in analytics["improvement_areas"]:
        if item not in weaknesses:
            weaknesses.append(item)

    return weaknesses[:3]
