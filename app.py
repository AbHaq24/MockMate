import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# Groq configuration
# -----------------------------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

MODEL_ID = "openai/gpt-oss-120b"


# -----------------------------
# Reusable LLM function
# -----------------------------
def ask(prompt, system_prompt="You are a helpful AI assistant."):
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="MockMate",
    page_icon="🎯",
    layout="centered"
)


# -----------------------------
# Custom CSS
# -----------------------------
st.markdown(
    """
    <style>

    /* =========================
       Overall page
       ========================= */

    .stApp {
        background-color: #f7f5f0;
    }

    .block-container {
        max-width: 720px;
        padding-top: 65px;
        padding-bottom: 60px;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }


    /* =========================
       Header
       ========================= */

    .mockmate-title {
        text-align: center;
        font-size: 48px;
        font-weight: 700;
        letter-spacing: -1px;
        margin-bottom: 4px;
        color: #222222;
    }

    .mockmate-tagline {
        text-align: center;
        font-size: 17px;
        color: #77736d;
        margin-bottom: 42px;
    }


    /* =========================
       Topic input
       ========================= */

    .topic-label {
        font-size: 15px;
        font-weight: 600;
        color: #333333;
        margin-bottom: 8px;
    }

    .stTextInput input {
        background-color: #ffffff;
        border: 1px solid #dedbd4;
        border-radius: 12px;
        padding: 14px;
        font-size: 15px;
        color: #222222;
    }

    .stTextInput input:focus {
        border-color: #aaa49a;
        box-shadow: none;
    }


    /* =========================
       Subject section
       ========================= */

    .subject-heading {
        text-align: center;
        color: #77736d;
        font-size: 14px;
        margin-top: 24px;
        margin-bottom: 15px;
    }


    /* =========================
       Subject buttons
       ========================= */

    .subject-button button {
        width: 70px !important;
        height: 70px !important;
        min-width: 70px !important;
        min-height: 70px !important;

        padding: 0 !important;

        border-radius: 50% !important;

        background-color: #ffffff !important;
        border: 1px solid #dedbd4 !important;

        color: #333333 !important;

        font-size: 12px !important;
        font-weight: 600 !important;

        display: flex !important;
        align-items: center !important;
        justify-content: center !important;

        margin: 0 auto !important;
    }

    .subject-button button:hover {
        background-color: #f0eee9 !important;
        border-color: #77736d !important;
        color: #111111 !important;
    }


    /* =========================
       Generate button
       ========================= */

    .generate-button button {
        width: 100% !important;
        height: 50px !important;

        border-radius: 12px !important;

        background-color: #5f6f52 !important;
        color: #ffffff !important;

        border: none !important;

        font-size: 16px !important;
        font-weight: 600 !important;

        margin-top: 25px !important;
    }

    .generate-button button:hover {
        background-color: #4f5f45 !important;
        color: #ffffff !important;
    }


    /* =========================
       Question container
       ========================= */

    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border-radius: 16px;
        margin-top: 32px;
    }

    .question-label {
        color: #77736d !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 15px;
    }

    .question-text {
        color: #222222 !important;
        font-size: 19px !important;
        line-height: 1.7 !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# -----------------------------
# Header
# -----------------------------

st.markdown(
    '<div class="mockmate-title">MockMate</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="mockmate-tagline">Practice. Think. Improve.</div>',
    unsafe_allow_html=True
)


# -----------------------------
# Session state
# -----------------------------

if "topic" not in st.session_state:
    st.session_state.topic = ""


# -----------------------------
# Topic input
# -----------------------------

st.markdown(
    '<div class="topic-label">What do you want to practice?</div>',
    unsafe_allow_html=True
)

topic = st.text_input(
    "",
    value=st.session_state.topic,
    placeholder="e.g. Machine Learning, SQL, GenAI...",
    label_visibility="collapsed"
)

st.session_state.topic = topic


# -----------------------------
# Subject shortcuts
# -----------------------------

st.markdown(
    '<div class="subject-heading">or pick a subject</div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)


with col1:
    st.markdown(
        '<div class="subject-button">',
        unsafe_allow_html=True
    )

    if st.button("ML"):
        st.session_state.topic = "Machine Learning"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


with col2:
    st.markdown(
        '<div class="subject-button">',
        unsafe_allow_html=True
    )

    if st.button("SQL"):
        st.session_state.topic = "SQL"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


with col3:
    st.markdown(
        '<div class="subject-button">',
        unsafe_allow_html=True
    )

    if st.button("Python"):
        st.session_state.topic = "Python"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


with col4:
    st.markdown(
        '<div class="subject-button">',
        unsafe_allow_html=True
    )

    if st.button("GenAI"):
        st.session_state.topic = "Generative AI"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------
# Generate Question button
# -----------------------------

st.markdown(
    '<div class="generate-button">',
    unsafe_allow_html=True
)

generate = st.button(
    "Generate Question",
    use_container_width=True
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)


# -----------------------------
# Generate question
# -----------------------------

if generate:

    prompt = f"""
    Generate ONE realistic Data Science interview question.

    Topic:
    {st.session_state.topic
     if st.session_state.topic
     else "Choose a random Data Science topic."}

    Return ONE interview question as a single clean paragraph.

    Do not use bullet points.
    Do not use numbered lists.
    Do not add headings.
    Do not provide the answer.
    Do not add quotation marks.
    """

    question = ask(
        prompt,
        system_prompt=(
            "You are an expert technical interviewer creating high-quality "
            "interview questions. "

            "Generate ONE realistic interview question based on the user's topic. "

            "Make the question clear, specific, practical, and relevant to an "
            "actual interview. "

            "Prioritize variety across different generations. "

            "Vary the question style between conceptual understanding, "
            "practical application, scenario-based problem solving, debugging, "
            "comparison and trade-offs, design, optimization, real-world "
            "decision making, experience-based questions, analytical reasoning, "
            "and coding-oriented questions when appropriate. "

            "Avoid generic textbook questions, simple definition-only questions, "
            "repetitive wording, repeated concepts, and obscure trivia. "

            "For each generation take a new topic, angle, subject, and question style. "

            "Return ONLY the interview question as one clean paragraph."
        )
    )

    # -----------------------------
    # Display generated question
    # -----------------------------

    with st.container(border=True):

        st.markdown(
            '<div class="question-label">'
            'Your Interview Question'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            f'<div class="question-text">'
            f'{question}'
            f'</div>',
            unsafe_allow_html=True
        )

