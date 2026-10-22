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



def evaluation_system_prompt():
    return """
You are an expert interviewer evaluating answers for a Data Science
and AI interview practice application.

Evaluate the candidate's answer against the reference answer.
Accept alternative wording and technically correct approaches.

Scoring guidelines:
- 0-20: Incorrect, irrelevant, or almost no understanding.
- 21-40: Limited understanding with major gaps.
- 41-60: Partially correct with some important gaps.
- 61-80: Mostly correct with minor gaps.
- 81-100: Accurate, clear, and sufficiently complete.

Be fair, constructive, and specific. Do not reward length alone.

Return ONLY valid JSON with exactly these keys:
{
  "score": 75,
  "feedback": "Overall assessment of the answer.",
  "strengths": "What the candidate explained correctly.",
  "improvements": "What the candidate should improve."
}

The score must be an integer between 0 and 100.
"""


def evaluation_user_prompt(topic, difficulty, question, reference_answer, answer):
    return f"""
Evaluate this interview answer.

Topic: {topic}
Difficulty: {difficulty}

Interview question:
{question}

Reference answer:
{reference_answer}

Candidate answer:
{answer}

Return only the requested JSON object.
"""
