import re
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
