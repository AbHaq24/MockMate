import json

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from backend.config.settings import get_settings

settings = get_settings()

client = OpenAI(
    api_key=settings.groq_api_key,
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0,
    max_retries=1,
)

MODEL_ID = settings.groq_model


def ask(prompt, system_prompt="You are a helpful AI assistant."):
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    except APITimeoutError as exc:
        raise RuntimeError("The AI request timed out. Please try again.") from exc
    except APIConnectionError as exc:
        raise RuntimeError("Could not connect to the AI service.") from exc
    except APIStatusError as exc:
        if exc.status_code == 429:
            raise RuntimeError(
                "The AI service rate limit was reached. Please try again later."
            ) from exc
        raise RuntimeError(
            f"The AI service returned an error (HTTP {exc.status_code})."
        ) from exc

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The AI service returned an empty response.")

    return content.strip()


def generate_question(topic, difficulty, previous_questions=None):
    from backend.prompts import question_system_prompt, question_user_prompt

    raw_response = ask(
        question_user_prompt(topic, difficulty, previous_questions),
        system_prompt=question_system_prompt(),
    )

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The AI returned an invalid question format.") from exc

    question = result.get("question")
    reference_answer = result.get("reference_answer")

    if not isinstance(question, str) or not question.strip():
        raise RuntimeError("The AI response did not contain a valid question.")

    if not isinstance(reference_answer, str) or not reference_answer.strip():
        raise RuntimeError("The AI response did not contain a valid reference answer.")

    return {
        "question": question.strip(),
        "reference_answer": reference_answer.strip(),
    }



def evaluate_answer(topic, difficulty, question, reference_answer, answer):
    from backend.prompts import (
        evaluation_system_prompt,
        evaluation_user_prompt,
    )

    raw_response = ask(
        evaluation_user_prompt(
            topic,
            difficulty,
            question,
            reference_answer,
            answer,
        ),
        system_prompt=evaluation_system_prompt(),
    )

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "The AI returned an invalid evaluation format."
        ) from exc

    score = result.get("score")
    if (
        not isinstance(score, int)
        or isinstance(score, bool)
        or not 0 <= score <= 100
    ):
        raise RuntimeError("The AI returned an invalid evaluation score.")

    for field in ("feedback", "strengths", "improvements"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            raise RuntimeError(
                f"The AI returned an invalid {field} field."
            )

    return {
        "score": score,
        "feedback": result["feedback"].strip(),
        "strengths": result["strengths"].strip(),
        "improvements": result["improvements"].strip(),
    }
