import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# Groq configuration
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL_ID = "openai/gpt-oss-120b"


# Reusable LLM function
def ask(prompt, system_prompt="You are a helpful AI assistant."):
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# MockMate
st.title("MockMate")
st.write("Practice. Think. Improve.")


topic = st.text_input(
    "Enter a topic, skill, or leave blank for a surprise question:"
)


if st.button("Generate Question"):

    prompt = f"""
    Generate ONE realistic Data Science interview question.

    Topic:
    {topic if topic else "Choose a random Data Science topic."}

    Return only the question.
    Do not provide the answer.
    """

    question = ask(
    prompt,
    system_prompt=(
        "You are an expert technical interviewer creating high-quality interview questions. "
        "Generate ONE realistic interview question based on the user's topic. "
        "Make the question clear, specific, practical, and relevant to an actual interview. "
        "Prioritize variety across different generations. Vary the question style between "
        "conceptual understanding, practical application, scenario-based problem solving, "
        "debugging, comparison and trade-offs, design, optimization, real-world decision making, "
        "experience-based questions, analytical reasoning, and coding-oriented questions when appropriate. "
        "Avoid generic textbook questions, simple definition-only questions, repetitive wording, "
        "repeated concepts, and obscure trivia. "
        "For each generate take a new topic,angle, subject and question style. "
        "Return ONLY the interview question."
    )
)

    st.subheader("Your Interview Question")
    st.write(question)



