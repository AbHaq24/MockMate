
import os
import datetime
import httpx
import streamlit as st
import extra_streamlit_components as stx

# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_URL = os.getenv(
    "MOCKMATE_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

REQUEST_TIMEOUT = 90.0

st.set_page_config(
    page_title="MockMate",
    page_icon="🎯",
    layout="centered",
)

cookie_manager = stx.CookieManager(key="mockmate_cookies")


# --------------------------------------------------
# Styling
# --------------------------------------------------

st.markdown(
    """
    <style>
    /* Page */
    .stApp {
        background-color: #f7f5f0;
        color: #222222;
    }

    .block-container {
        max-width: 760px;
        padding-top: 35px;
        padding-bottom: 50px;
    }

    /* App title */
    .mockmate-title {
        text-align: center;
        font-size: 44px;
        font-weight: 700;
        color: #222222 !important;
    }

    .mockmate-tagline {
        text-align: center;
        color: #444444 !important;
        margin-bottom: 30px;
    }

    /* General text and headings */
    .stApp p,
    .stApp li,
    .stApp label,
    .stMarkdown,
    .stMarkdown p,
    .stMarkdown strong,
    [data-testid="stCaptionContainer"] p,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] span {
        color: #222222 !important;
        -webkit-text-fill-color: #222222 !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #222222 !important;
    }

    /* Primary buttons: dark background, white text */
    .stButton button,
    [data-testid="stFormSubmitButton"] button {
        background-color: #20232b !important;
        color: #ffffff !important;
        border: 1px solid #20232b !important;
        border-radius: 10px;
        min-height: 42px;
    }

    .stButton button p,
    .stButton button span,
    [data-testid="stFormSubmitButton"] button p,
    [data-testid="stFormSubmitButton"] button span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    .stButton button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #3b4252 !important;
        border-color: #3b4252 !important;
    }

    /* Text inputs and answer area */
    .stTextInput input,
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #222222 !important;
        -webkit-text-fill-color: #222222 !important;
        border: 1px solid #a8a8a8 !important;
        border-radius: 8px;
    }

    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #666666 !important;
        -webkit-text-fill-color: #666666 !important;
        opacity: 1 !important;
    }

    /* Login / Create account selector */
    div[role="radiogroup"] label,
    div[role="radiogroup"] label p,
    div[role="radiogroup"] label span {
        color: #222222 !important;
        -webkit-text-fill-color: #222222 !important;
        opacity: 1 !important;
    }

    /* Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border: 1px solid #dedbd4;
        border-radius: 14px;
    }

    /* Progress bar */
    [data-testid="stProgress"] > div {
        background-color: #dedbd4;
    }

    [data-testid="stProgress"] [data-testid="stProgressBar"] {
        background-color: #2563eb;
    }

    /* Success, error and warning messages */
    [data-testid="stAlert"] p {
        color: #222222 !important;
    }

    /* Fix inline code formatting in generated questions */
    .stMarkdown code {
       color: #222222 !important;
       -webkit-text-fill-color: #222222 !important;
      background-color: #eeeae2 !important;
      border: 1px solid #dedbd4 !important;
      border-radius: 5px;
      padding: 2px 5px;
      font-size: 0.9em;
    }

    /* Generated question card: force readable dark text */
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown,
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown p,
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown strong,
    div[data-testid="stVerticalBlockBorderWrapper"] .stMarkdown li {
     color: #222222 !important;
     -webkit-text-fill-color: #222222 !important;
}

/* Ensure the question container has a white background */
    div[data-testid="stVerticalBlockBorderWrapper"] {
     background-color: #ffffff !important;
     color: #222222 !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="mockmate-title">MockMate</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="mockmate-tagline">'
    'Practice. Think. Improve.'
    '</div>',
    unsafe_allow_html=True,
)


# Session state
# --------------------------------------------------

DEFAULTS = {
    "token": None,
    "email": "",
    "topic": "Machine Learning",
    "difficulty": "Medium",
    "assessment_id": None,
    "assessment_status": None,
    "questions_shown_count": 0,
    "current_question": None,
    "evaluation": None,
    "finish_message": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value



# --------------------------------------------------
# API helper
# --------------------------------------------------


def api_request(method, path, payload=None):
    headers = {}

    if st.session_state.token:
        headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )

    try:
        response = httpx.request(
            method,
            f"{API_URL}{path}",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.RequestError as exc:
        raise RuntimeError(
            "Cannot connect to MockMate API. "
            "Make sure the FastAPI server is running."
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    # Handle API errors, including expired authentication tokens
    if not response.is_success:
        if (
            response.status_code == 401
            and path != "/auth/login"
        ):
            st.session_state.token = None
            st.session_state.email = ""
            reset_assessment()
            st.rerun()

        detail = data.get("detail", response.text)

        if isinstance(detail, list):
            detail = "; ".join(
                str(item.get("msg", item))
                if isinstance(item, dict)
                else str(item)
                for item in detail
            )

        raise RuntimeError(
            f"API error ({response.status_code}): {detail}"
        )

    # Return successful responses, including HTTP 201
    return data

saved_token = cookie_manager.get("mockmate_token")

if not st.session_state.token and saved_token:
    st.session_state.token = saved_token

    try:
        user = api_request("GET", "/auth/me")
        st.session_state.email = user.get("email", "")
    except RuntimeError:
        cookie_manager.delete("mockmate_token")
        st.session_state.token = None
        st.session_state.email = ""

# --------------------------------------------------
# Assessment helpers
# --------------------------------------------------

def generate_question():
    assessment_id = st.session_state.assessment_id

    question = api_request(
        "POST",
        f"/assessments/{assessment_id}/questions",
    )

    st.session_state.current_question = question
    st.session_state.questions_shown_count = (
        question["display_number"]
    )


def reset_assessment():
    st.session_state.assessment_id = None
    st.session_state.assessment_status = None
    st.session_state.questions_shown_count = 0
    st.session_state.current_question = None
    st.session_state.evaluation = None
    st.session_state.finish_message = None


# --------------------------------------------------
# Authentication
# --------------------------------------------------
if st.session_state.get("switch_to_login", False):
    st.session_state.auth_mode = "Login"
    st.session_state.switch_to_login = False

if not st.session_state.token:
    auth_mode = st.radio(
        "Authentication",
        ["Login", "Create account"],
        horizontal=True,
        label_visibility="visible",
        key="auth_mode",
    )

    if auth_mode == "Login":
        with st.form("login_form"):
            login_email = st.text_input("Email")
            login_password = st.text_input(
                "Password",
                type="password",
            )

            login_clicked = st.form_submit_button(
                "Login",
                use_container_width=True,
            )

        if login_clicked:
            try:
                result = api_request(
                    "POST",
                    "/auth/login",
                    {
                        "email": login_email.strip(),
                        "password": login_password,
                    },
                )

                st.session_state.token = result["access_token"]
                st.session_state.email = login_email.strip()


                cookie_manager.set(
                    "mockmate_token",
                     result["access_token"],
                     expires_at=datetime.datetime.now()
                      + datetime.timedelta(days=1),
                )







                reset_assessment()
                st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))

    else:
        with st.form("register_form"):
            register_email = st.text_input(
                "Email address",
                key="register_email",
            )
            register_password = st.text_input(
                "Password (at least 8 characters)",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
            )

            register_clicked = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if register_clicked:
            if register_password != confirm_password:
                st.error("The passwords do not match.")
            elif len(register_password) < 8:
                st.error("Password must contain at least 8 characters.")
            else:
                try:
                    api_request(
                        "POST",
                        "/auth/register",
                        {
                            "email": register_email.strip(),
                            "password": register_password,
                        },
                    )

                    st.session_state.switch_to_login = True
                    st.success("Account created. Please log in.")
                    st.rerun()

                except RuntimeError as exc:
                    st.error(str(exc))

    st.stop()


# Logged-in header
# --------------------------------------------------

st.caption(f"Logged in as {st.session_state.email}")

if st.button("Logout"):
    try:
        cookie_manager.delete("mockmate_token")
    except KeyError:
        pass

    st.session_state.token = None
    st.session_state.email = ""

    reset_assessment()
    st.rerun()



# --------------------------------------------------
# Assessment History
# --------------------------------------------------

st.divider()
st.subheader("Assessment History")

if st.button("Refresh History"):
    st.rerun()


try:
    history = api_request("GET", "/assessments")

    # Performance Dashboard
    completed_scores = [
        item["score"]
        for item in history
        if item["status"] == "completed"
        and item.get("score") is not None
    ]

    total_completed = len(completed_scores)
    average_score = (
        sum(completed_scores) / total_completed
        if total_completed
        else 0
    )
    best_score = (
        max(completed_scores)
        if completed_scores
        else 0
    )

    st.subheader("Performance Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric("Evaluated Assessments", total_completed)
    col2.metric("Average Score", f"{average_score:.1f}/100")
    col3.metric("Best Score", f"{best_score}/100")

    st.divider()
    st.subheader("Previous Assessments")

    if not history:
        st.info("No previous assessments found.")
    else:
        for item in history:
            score = item.get("score")
            score_text = (
                f"{score}/100"
                if score is not None
                else "Not evaluated"
            )

            with st.expander(
                f"Assessment #{item['assessment_id']} — "
                f"{item['topic']} — {score_text}"
            ):
                st.write(f"**Difficulty:** {item['difficulty']}")
                st.write(f"**Status:** {item['status']}")

                if item.get("feedback"):
                    st.write("**Feedback**")
                    st.write(item["feedback"])

                if item.get("strengths"):
                    st.write("**Strengths**")
                    st.write(item["strengths"])

                if item.get("improvements"):
                    st.write("**Areas to improve**")
                    st.write(item["improvements"])

except RuntimeError as exc:
    st.error(f"Could not load assessment history: {exc}")


# --------------------------------------------------
# Evaluation results
# --------------------------------------------------

if st.session_state.evaluation:
    result = st.session_state.evaluation

    st.success("Assessment completed!")

    st.metric("Your score", f"{result['score']}/100")

    st.subheader("Feedback")
    st.write(result["feedback"])

    st.subheader("Strengths")
    st.write(result["strengths"])

    st.subheader("Areas to improve")
    st.write(result["improvements"])

    if st.button(
        "Start a new assessment",
        use_container_width=True,
    ):
        reset_assessment()
        st.rerun()

    st.stop()


# --------------------------------------------------
# Completed without an answer
# --------------------------------------------------

if st.session_state.assessment_status == "completed":
    st.info(
        st.session_state.finish_message
        or "Assessment completed without an evaluated answer."
    )

    if st.button(
        "Start a new assessment",
        use_container_width=True,
    ):
        reset_assessment()
        st.rerun()

    st.stop()


# --------------------------------------------------
# Start an assessment
# --------------------------------------------------

if st.session_state.assessment_id is None:
    st.subheader("Prepare for your interview")

    with st.form("assessment_form"):
        topic = st.text_input(
            "What do you want to practice?",
            value=st.session_state.topic,
            max_chars=100,
            placeholder="e.g. Machine Learning, SQL, GenAI",
        )

        difficulty = st.selectbox(
            "Difficulty",
            ["Easy", "Medium", "Hard"],
            index=["Easy", "Medium", "Hard"].index(
                st.session_state.difficulty
            ),
        )

        start_clicked = st.form_submit_button(
            "Start assessment",
            use_container_width=True,
        )

    if start_clicked:
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            try:
                assessment = api_request(
                    "POST",
                    "/assessments",
                    {
                        "topic": topic.strip(),
                        "difficulty": difficulty,
                    },
                )

                st.session_state.topic = topic.strip()
                st.session_state.difficulty = difficulty
                st.session_state.assessment_id = assessment[
                    "id"
                ]
                st.session_state.assessment_status = (
                    assessment["status"]
                )

                with st.spinner("Generating your question..."):
                    generate_question()

                st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))

    st.stop()


# --------------------------------------------------
# Active assessment
# --------------------------------------------------

assessment_id = st.session_state.assessment_id
current = st.session_state.current_question

st.subheader(st.session_state.topic)

st.caption(
    f"Difficulty: {st.session_state.difficulty} · "
    f"Questions generated: "
    f"{st.session_state.questions_shown_count}/3"
)

st.progress(
    st.session_state.questions_shown_count / 3
)


# --------------------------------------------------
# Display current question and answer form
# --------------------------------------------------

if current:
    st.markdown(
        f"**Question {current['display_number']} of 3**"
        f" · Version {current['version_number']}"
    )

    with st.container(border=True):
        st.markdown(current["question"])

    answer_text = st.text_area(
        "Your answer",
        key=f"answer_{current['assessment_question_id']}",
        height=180,
        max_chars=10000,
        placeholder="Explain your approach and reasoning...",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        submit_clicked = st.button(
            "Submit answer",
            type="primary",
            use_container_width=True,
        )

    with col2:
        regenerate_clicked = st.button(
            "Try another",
            use_container_width=True,
        )

    with col3:
        skip_clicked = st.button(
            "Skip question",
            use_container_width=True,
        )

    if submit_clicked:
        if not answer_text.strip():
            st.warning("Please enter an answer first.")
        else:
            try:
                with st.spinner("Evaluating your answer..."):
                    result = api_request(
                        "POST",
                        f"/assessments/{assessment_id}/"
                        f"questions/"
                        f"{current['assessment_question_id']}/answer",
                        {"answer_text": answer_text.strip()},
                    )

                st.session_state.evaluation = result
                st.session_state.assessment_status = "completed"
                st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))

    if regenerate_clicked:
        try:
            with st.spinner("Generating an alternative..."):
                question = api_request(
                    "POST",
                    f"/assessments/{assessment_id}/"
                    f"questions/"
                    f"{current['display_number']}/regenerate",
                )

            st.session_state.current_question = question
            st.rerun()

        except RuntimeError as exc:
            st.error(str(exc))

    if skip_clicked:
        st.session_state.current_question = None
        st.rerun()


# --------------------------------------------------
# Generate next question or finish
# --------------------------------------------------

else:
    count = st.session_state.questions_shown_count

    if count < 3:
        if st.button(
            "Generate next question",
            type="primary",
            use_container_width=True,
        ):
            try:
                with st.spinner("Generating your question..."):
                    generate_question()
                st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))

    else:
        st.info(
            "You have used all three question slots. "
            "You can finish without submitting an answer."
        )

        if st.button(
            "Finish assessment",
            type="primary",
            use_container_width=True,
        ):
            try:
                result = api_request(
                    "POST",
                    f"/assessments/{assessment_id}/finish",
                )

                st.session_state.assessment_status = (
                    result["status"]
                )
                st.session_state.finish_message = (
                    result["message"]
                )
                st.rerun()

            except RuntimeError as exc:
                st.error(str(exc))
