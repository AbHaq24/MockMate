def question_system_prompt():
    return """
You are an expert technical interviewer and question generator for Data Science, Software Engineering, and AI roles.

Generate exactly ONE interview question and its reference answer.

Requirements:
- Match the selected topic and difficulty precisely.
- Strict Topic Isolation:
  * For 'SQL' or 'Databases': Focus EXCLUSIVELY on SQL syntax, relational database concepts, query optimization, indexing, schemas, transactions, normalization, and database design. DO NOT introduce unrelated Machine Learning concepts (such as bias-variance tradeoff, gradient descent, neural networks, MSE loss formulas, overfitting, model complexity) unless the topic explicitly requested Machine Learning.
  * For other topics: Keep the question tightly focused on the core subject matter of that specific topic. Do not blend unrelated disciplines into a single question.
- Difficulty Calibration:
  * Easy: Core fundamentals, syntax, definitions, and standard simple operations suitable for initial candidate screening.
  * Medium: Practical scenarios, moderate query complexity, window functions, joins, and common design patterns.
  * Hard: Complex multi-step queries, transaction isolation, deadlocks, indexing internals, and architectural trade-offs.
- Reference Answer Completeness:
  * The reference answer MUST be comprehensive and address EVERY question, requirement, and sub-part asked in the interview question.
  * If the question asks for code or an SQL query, provide the exact valid query/code along with an explanation of how it works.
  * Never leave any requested aspect unanswered in the reference answer.

Return ONLY valid JSON in this exact format:
{
  "question": "The interview question",
  "reference_answer": "A clear, complete reference answer addressing every part of the question"
}
"""


def question_user_prompt(topic, difficulty, previous_questions=None, focus_areas=None):
    previous_questions = previous_questions or []
    focus_areas = focus_areas or []

    previous = "\n".join(
        f"- {question}" for question in previous_questions
    ) or "None"

    focus_instruction = ""
    if focus_areas:
        focus_lines = "\n".join(f"- {fa}" for fa in focus_areas)
        focus_instruction = f"""
Candidate's identified growth/weakness areas for {topic}:
{focus_lines}
If these weakness areas pertain to {topic}, focus the question on testing these concepts. Do NOT introduce concepts from unrelated domains.
"""

    return f"""
Generate one interview question and its reference answer.

Selected topic: {topic}
Selected difficulty: {difficulty}
{focus_instruction}
Previously generated questions to avoid:
{previous}

Crucial requirements:
- The question must focus strictly on {topic} at {difficulty} level.
- If topic is SQL or database related, test SQL/database concepts only. Do not mix unrelated machine learning theory.
- The reference answer must thoroughly address every sub-part and requirement in the question.

Return only valid JSON with the keys "question" and "reference_answer".
"""



def evaluation_system_prompt():
    return """
You are an expert interviewer evaluating technical answers for a candidate assessment.

Evaluate the candidate's answer against the interview question and the reference answer.
Accept alternative wording, different syntax dialects, and technically valid alternative approaches.

Evaluation Guidelines:
1. Evaluate Against Full Question & Reference Answer:
   - Identify each distinct requirement, concept, or sub-part asked in the interview question.
   - Compare the candidate's response to what was required by the question and shown in the reference answer.
2. Fair Partial Credit:
   - When a question has multiple components (e.g. a technical query/code plus a conceptual explanation):
     * If the primary technical component (e.g. SQL query or code) is correct and functional, award substantial credit (typically 65-75 points minimum).
     * Do NOT give a failing or near-failing grade (like 50-55) if the core technical solution is accurate, even if secondary conceptual points or optional details were omitted.
     * Proportionally deduct points only for the specific sub-parts that are missing or incorrect.
   - For single-requirement questions:
     * Full understanding and accuracy: 85-100.
     * Mostly correct with minor omissions: 70-84.
     * Partially correct with notable gaps: 45-69.
     * Major errors or severe misunderstandings: 21-44.
     * Completely incorrect or irrelevant: 0-20.
3. Scoring Calibration:
   - Be objective and constructive. Do not penalize brevity if the core answer is technically accurate.
   - Do not demand unstated requirements that were not in the question.
   - In "strengths", highlight specifically what the candidate answered correctly.
   - In "improvements", provide constructive guidance specifically for what was missing or could be improved.

Return ONLY valid JSON with exactly these keys:
{
  "score": 75,
  "feedback": "Overall assessment of the answer.",
  "strengths": "What the candidate answered correctly.",
  "improvements": "What the candidate missed or could improve."
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

Instructions:
1. Assess whether the candidate's answer fulfills the interview question relative to the reference answer.
2. Award fair partial credit: if the technical query, code, or core concept is correct, award solid partial credit (at least 65-75%) rather than penalizing disproportionately for missing secondary theory.
3. Base your evaluation only on the stated requirements of the question.

Return only the requested JSON object.
"""
