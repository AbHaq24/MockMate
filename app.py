import streamlit as st
from backend.llm import ask
from backend.prompts import question_system_prompt, question_user_prompt


# -----------------------------
# Page configuration
# -----------------------------

st.set_page_config(
    page_title="MockMate",
    page_icon="",
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
       Section headings
       ========================= */

    .subject-heading,
    .difficulty-heading {
        text-align: center;
        color: #77736d;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 15px;
    }

    .subject-heading {
        margin-top: 24px;
    }

    .difficulty-heading {
        margin-top: 28px;
    }


    /* =========================
       All selection buttons
       ========================= */

    div[data-testid="stButton"] button {
        border-radius: 12px !important;
        height: 50px !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }


    /* =========================
       Unselected buttons
       ========================= */

    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 1px solid #dedbd4 !important;
        color: #333333 !important;
    }

    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background-color: #f0eee9 !important;
        border-color: #77736d !important;
        color: #111111 !important;
    }


    /* =========================
       Selected buttons
       ========================= */

    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #5f6f52 !important;
        border: 1px solid #5f6f52 !important;
        color: #ffffff !important;
    }

    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #5f6f52 !important;
        border-color: #5f6f52 !important;
        color: #ffffff !important;
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

if "difficulty" not in st.session_state:
    st.session_state.difficulty = "Medium"

if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = ""


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
    '<div class="subject-heading">Select a subject</div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)


with col1:
    if st.button(
        "ML",
        key="ml_button",
        type=(
            "primary"
            if st.session_state.selected_subject == "Machine Learning"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.topic = "Machine Learning"
        st.session_state.selected_subject = "Machine Learning"
        st.rerun()


with col2:
    if st.button(
        "SQL",
        key="sql_button",
        type=(
            "primary"
            if st.session_state.selected_subject == "SQL"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.topic = "SQL"
        st.session_state.selected_subject = "SQL"
        st.rerun()


with col3:
    if st.button(
        "Python",
        key="python_button",
        type=(
            "primary"
            if st.session_state.selected_subject == "Python"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.topic = "Python"
        st.session_state.selected_subject = "Python"
        st.rerun()


with col4:
    if st.button(
        "GenAI",
        key="genai_button",
        type=(
            "primary"
            if st.session_state.selected_subject == "Generative AI"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.topic = "Generative AI"
        st.session_state.selected_subject = "Generative AI"
        st.rerun()


# -----------------------------
# Difficulty
# -----------------------------

st.markdown(
    '<div class="difficulty-heading">Select difficulty level</div>',
    unsafe_allow_html=True
)

diff1, diff2, diff3 = st.columns(3)


with diff1:
    if st.button(
        "Easy",
        key="easy_button",
        type=(
            "primary"
            if st.session_state.difficulty == "Easy"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.difficulty = "Easy"
        st.rerun()


with diff2:
    if st.button(
        "Medium",
        key="medium_button",
        type=(
            "primary"
            if st.session_state.difficulty == "Medium"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.difficulty = "Medium"
        st.rerun()


with diff3:
    if st.button(
        "Hard",
        key="hard_button",
        type=(
            "primary"
            if st.session_state.difficulty == "Hard"
            else "secondary"
        ),
        use_container_width=True
    ):
        st.session_state.difficulty = "Hard"
        st.rerun()


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

    topic = (
        st.session_state.topic
        if st.session_state.topic
        else "Choose a random Data Science topic."
    )

    prompt = question_user_prompt(
        topic,
        st.session_state.difficulty
    )

    question = ask(
        prompt,
        system_prompt=question_system_prompt()
    )

    st.session_state.question = question


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