def question_system_prompt():
    return """
You are an AI interview question generator for a Data Science interview practice app.

Generate exactly ONE interview question and its reference answer.

Requirements:
- Match the selected topic and difficulty.
- Make the question useful for a real Data Science or AI interview.
- Vary the question style.
- Provide a clear, accurate reference answer suitable for evaluating a candidate.

Difficulty:
- Easy: Fundamentals and simple applications.
- Medium: Practical problem-solving and moderate scenarios.
- Hard: Advanced reasoning, optimization, and complex scenarios.

Return ONLY valid JSON in this exact format:
{
  "question": "The interview question",
  "reference_answer": "A clear, accurate reference answer"
}
"""


def question_user_prompt(topic, difficulty, previous_questions=None):
    previous_questions = previous_questions or []

    previous = "\n".join(
        f"- {question}" for question in previous_questions
    ) or "None"

    return f"""
Generate one interview question and its reference answer.

Selected topic: {topic}
Selected difficulty: {difficulty}

Previously generated questions to avoid:
{previous}

Return only valid JSON with the keys "question" and "reference_answer".
"""