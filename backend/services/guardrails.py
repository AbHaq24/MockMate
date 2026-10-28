import re
from typing import Optional
from fastapi import HTTPException

# Known prompt injection and system override patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|directions)",
    r"(reveal|show|print|leak|output)\s+(the\s+)?(system\s+prompt|developer\s+mode|instructions)",
    r"you\s+are\s+now\s+(a|an)?\s*(dan|developer|jailbroken|unrestricted|god)",
    r"dan\s+mode|jailbreak|bypass\s+filter|override\s+safety",
    r"<script[\s\S]*?>[\s\S]*?<\/script>",
    r"javascript:\s*",
    r"(\bunion\b\s+\bselect\b|\bdrop\b\s+\btable\b|\binsert\b\s+\binto\b)",
    r"exec\s*\(|eval\s*\(|import\s+os|system\s*\(",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+an?\s+unfiltered",
    r"give\s+(me|this|candidate)\s+(a\s+)?score\s+of\s+100",
    r"output\s+only\s*\{\s*\"score\"\s*:\s*100",
]

# Sensitive, unsafe, or harmful topics disallowed in technical interview assessments
PROHIBITED_THEMES = [
    r"\b(bomb|weapon|explosive|bioweapon|poison|meth|heroin|fentanyl)\b",
    r"\b(hack\s+into|ddos\s+attack|exploit\s+vulnerability|ransomware\s+creation)\b",
    r"\b(hate\s+speech|slur|genocide|nazi)\b",
    r"\b(suicide|self-harm|torture)\b",
]

# Machine Learning / AI concepts that must not be forced into pure SQL & Database questions
UNRELATED_ML_CONCEPTS_IN_SQL = [
    r"bias[- ]variance",
    r"overfitting|underfitting",
    r"gradient\s+descent",
    r"neural\s+network|backpropagation|activation\s+function",
    r"random\s+forest|logistic\s+regression|decision\s+tree|support\s+vector",
    r"hyperparameter",
    r"mean\s+squared\s+error|\bmse\b",
    r"loss\s+function|cross[- ]entropy",
    r"clustering|k[- ]means",
    r"deep\s+learning|transformer|attention\s+mechanism",
    r"model\s+complexity|optimal\s+complexity",
]


def is_sql_or_db_topic(topic: str) -> bool:
    """Check if the topic is pure SQL or Relational Database without explicit ML intent."""
    if not topic or not isinstance(topic, str):
        return False
    clean = topic.strip().lower()
    has_sql_or_db = bool(
        re.search(
            r"\b(sql|database|databases|postgres|postgresql|mysql|sqlite|rdbms|relational|nosql|query|queries)\b",
            clean,
        )
    )
    has_ml_intent = bool(
        re.search(
            r"\b(ml|machine\s+learning|ai|deep\s+learning|data\s+science|neural)\b",
            clean,
        )
    )
    return has_sql_or_db and not has_ml_intent


def validate_question_topic_consistency(
    topic: str, question_text: str
) -> tuple[bool, Optional[str]]:
    """Validate whether an interview question is strictly consistent with its topic.

    Rejects questions that mix unrelated domains (e.g. demanding ML theory in a pure SQL question).
    Returns (is_valid, rejection_reason).
    """
    if not question_text or not isinstance(question_text, str):
        return False, "Question text cannot be empty."

    clean_q = question_text.strip()
    if len(clean_q) < 10:
        return False, "Question text is too short."

    # If pure SQL / Database topic, enforce strict isolation from unrelated ML theory
    if is_sql_or_db_topic(topic):
        for pattern in UNRELATED_ML_CONCEPTS_IN_SQL:
            if re.search(pattern, clean_q, re.IGNORECASE):
                return (
                    False,
                    f"Mixed topic detected: SQL question contains unrelated Machine Learning theory matching '{pattern}'.",
                )

    return True, None


def validate_reference_answer_completeness(
    question_text: str, reference_answer: str
) -> tuple[bool, Optional[str]]:
    """Verify that a reference answer adequately addresses every part of the question.

    Returns (is_complete, rejection_reason).
    """
    if not reference_answer or not isinstance(reference_answer, str):
        return False, "Reference answer cannot be empty."

    clean_ref = reference_answer.strip()
    if len(clean_ref) < 15:
        return False, "Reference answer is too brief to provide an evaluation baseline."

    clean_q = question_text.strip().lower()

    # If question asks to write a query AND explain conceptually
    asks_query = bool(
        re.search(
            r"\b(write|create|provide|construct|give)\s+(an?\s+)?(sql\s+)?query\b",
            clean_q,
        )
    )
    asks_explanation = bool(
        re.search(
            r"\b(explain|describe|why|how\s+does|what\s+is|discuss)\b",
            clean_q,
        )
    )

    if asks_query and asks_explanation:
        has_sql_syntax = bool(
            re.search(
                r"\b(select|from|where|group\s+by|insert|update|delete|with)\b",
                clean_ref,
                re.IGNORECASE,
            )
        )
        words = clean_ref.split()
        has_adequate_explanation = len(words) >= 14

        if not has_sql_syntax:
            return (
                False,
                "Question asks for a query and explanation, but reference answer lacks SQL query syntax.",
            )
        if not has_adequate_explanation:
            return (
                False,
                "Question asks for a query and explanation, but reference answer explanation is incomplete.",
            )

    return True, None


def validate_topic_guardrails(topic: str) -> str:
    """Validate and sanitize user-submitted assessment topic.

    Guards against prompt injections, off-topic abuse, and harmful inputs.
    """
    if not topic or not isinstance(topic, str):
        raise HTTPException(
            status_code=422,
            detail="Topic cannot be blank.",
        )

    clean_topic = topic.strip()

    # 1. Length guardrails
    if len(clean_topic) < 2:
        raise HTTPException(
            status_code=422,
            detail="Topic is too short. Please provide a descriptive topic (at least 2 characters).",
        )

    if len(clean_topic) > 100:
        raise HTTPException(
            status_code=422,
            detail="Topic exceeds the maximum allowed length of 100 characters.",
        )

    # 2. Minimum educational content (must contain recognizable letters)
    letters = re.findall(r"[A-Za-z]", clean_topic)
    if len(letters) < 2:
        raise HTTPException(
            status_code=422,
            detail="Topic must contain recognizable subject words.",
        )

    # 3. Prompt injection guardrail
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, clean_topic, re.IGNORECASE):
            raise HTTPException(
                status_code=422,
                detail="Invalid topic detected. Assessment topics must not contain system prompt override instructions.",
            )

    # 4. Prohibited themes guardrail
    for pattern in PROHIBITED_THEMES:
        if re.search(pattern, clean_topic, re.IGNORECASE):
            raise HTTPException(
                status_code=422,
                detail="This topic falls outside of MockMate's educational policy.",
            )

    # Sanitize multiple consecutive whitespaces
    return re.sub(r"\s+", " ", clean_topic)


def validate_answer_guardrails(answer_text: str) -> str:
    """Validate candidate answer for length and prompt injection safeguards."""
    if not answer_text or not isinstance(answer_text, str):
        raise HTTPException(
            status_code=422,
            detail="Answer cannot be blank.",
        )

    clean_answer = answer_text.strip()

    if not clean_answer:
        raise HTTPException(
            status_code=422,
            detail="Answer cannot be blank.",
        )

    if len(clean_answer) > 10000:
        raise HTTPException(
            status_code=422,
            detail="Answer exceeds the maximum allowed length of 10,000 characters.",
        )

    # Check for direct prompt injection attempt in answer
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, clean_answer, re.IGNORECASE):
            raise HTTPException(
                status_code=422,
                detail="Answer contains disallowed prompt injection instructions.",
            )

    return clean_answer
