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
            "You are an experienced Data Science interviewer. "
            "Create varied, practical, and relevant interview questions."
        )
    )

    st.subheader("Your Interview Question")
    st.write(question)