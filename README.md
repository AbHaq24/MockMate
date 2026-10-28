# MockMate: AI-Powered Technical Interview Preparation Platform

MockMate is an end-to-end technical mock interview platform tailored for Data Science, Machine Learning, and SQL candidates. It provides curriculum-grounded question retrieval, LLM-powered dynamic question generation via Groq, structured rubric-based evaluation with strict guardrails, and candidate analytics tracking strengths and weaknesses over time.

---

## Architecture Overview

```
                        +----------------------------+
                        |     Streamlit Frontend     |
                        | (Candidate Assessment UI)  |
                        +--------------+-------------+
                                       |
                               HTTP / REST API
                                       |
                                       v
                        +----------------------------+
                        |      FastAPI Backend       |
                        |   (Auth, Questions, Eval)  |
                        +-------+------------+-------+
                                |            |
          +---------------------+            +---------------------+
          |                                                        |
          v                                                        v
+-------------------+                                    +-------------------+
|    PostgreSQL     |                                    |     Groq API      |
| (SQLAlchemy 2.0 & |                                    | (openai/gpt-oss-  |
| Alembic Migration)|                                    |       120b)       |
+-------------------+                                    +-------------------+
```

### Technology Stack
- **Backend**: FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, SlowAPI, Pytest
- **Frontend**: Streamlit, Requests
- **Database**: PostgreSQL with `psycopg` (v3)
- **AI/LLM**: Groq Cloud API (`openai/gpt-oss-120b`)
- **Containerization**: Docker (multi-stage) & Docker Compose
- **CI/CD**: GitHub Actions (`.github/workflows/ci.yml`) & Render Blueprint (`render.yaml`)
- **Performance Testing**: Locust

---

## Local Development Setup

### 1. Prerequisites
- Python 3.13+ installed
- PostgreSQL 15+ installed and running locally
- A free Groq API key from [Groq Console](https://console.groq.com/keys)

### 2. Virtual Environment Setup
Clone the repository and create an isolated virtual environment:

```bash
git clone https://github.com/AbHaq24/MockMate.git
cd MockMate

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Copy the configuration template:

```bash
cp .env.example .env
```

Open `.env` and fill in your local settings:

```ini
APP_NAME="MockMate API"
APP_VERSION="0.1.0"
ENVIRONMENT="development"
RATE_LIMIT_ENABLED=true

# Local PostgreSQL connection (adjust credentials/port as needed)
DATABASE_URL="postgresql+psycopg://postgres:your_password@localhost:5432/mockmate_db"

# Groq API configuration
GROQ_API_KEY="gsk_your_groq_api_key_here"
GROQ_MODEL="openai/gpt-oss-120b"

# JWT configuration (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET_KEY="your_secure_random_jwt_secret_key_minimum_32_characters"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS & Frontend URLs
CORS_ORIGINS="http://localhost:8501,http://127.0.0.1:8501"
MOCKMATE_API_URL="http://127.0.0.1:8000"
```

> **Security Note:** Never commit `.env` or real API keys to version control. `.env` is ignored in `.gitignore` and `.dockerignore`.

### 4. Database Setup & Alembic Migrations
Ensure your local PostgreSQL database exists, then apply migrations:

```bash
alembic upgrade head
```

### 5. Running the Application Locally
In one terminal, start the FastAPI backend:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Backend API documentation is available at: `http://127.0.0.1:8000/docs`

In a second terminal, start the Streamlit frontend:

```bash
streamlit run frontend/app.py --server.port 8501
```
The candidate interface is accessible at: `http://localhost:8501`

---

## Running with Docker & Docker Compose

MockMate includes a production-grade multi-stage Docker build and an isolated Compose environment.

### Compose Port Architecture
To protect your local workstation's native PostgreSQL instance (default port 5432), the Docker Compose database container is mapped to host port **5433**:
- **`mockmate-db`**: Host port `5433` -> Container port `5432` (named volume: `mockmate_postgres_data`)
- **`mockmate-backend`**: Host port `8000` -> Container port `8000` (FastAPI)
- **`mockmate-frontend`**: Host port `8501` -> Container port `8501` (Streamlit)

### 1. Build and Start the Stack
```bash
docker compose up -d --build
```

### 2. Verify Container Health
```bash
docker compose ps
```
All three containers should report `(healthy)`. Backend automatically awaits database health and runs `alembic upgrade head` before starting Uvicorn.

### 3. View Service Logs
```bash
# All services
docker compose logs -f

# Backend only
docker compose logs -f backend

# Frontend only
docker compose logs -f frontend
```

### 4. Stop the Stack
```bash
# Stop containers while preserving data volume
docker compose down

# Stop containers and remove volume (Destructive to container data)
docker compose down -v
```

---

## Running the Test Suite

MockMate includes a complete test suite covering authentication, question guardrails, retrieval, evaluation rubrics, analytics, and topic consistency.

```bash
# Run all tests with duration reporting
pytest -v --durations=10

# Run in quiet mode
pytest -q
```

All 71 tests use an isolated in-memory test database and mock LLM calls, ensuring fast, deterministic, and safe local execution without consuming Groq API credits.

---

## Load & Performance Testing (Locust)

MockMate includes a dedicated Locust load-testing suite in `locustfile.py`.

### ⚠️ Critical LLM Safety Guardrail
The Locust load test intentionally targets **safe, non-LLM endpoints** (`/health`, `/auth/register`, `/auth/login`, `/auth/me`, `/assessments`, `/assessments/analytics`).
**Question generation (`/questions`) and answer evaluation (`/answer`) are strictly excluded** from load tests to prevent:
1. Flooding the Groq Cloud API.
2. Exceeding LLM rate limits.
3. Incurring unexpected external billing costs.

### 1. Install Load Testing Dependencies
Locust is defined in `requirements-dev.txt` to keep the production container lean:

```bash
pip install -r requirements-dev.txt
```

### 2. Running a Fast Headless Smoke Test
Run a 10-second headless smoke test against the local backend (5 concurrent users, spawn rate of 2):

```bash
locust -f locustfile.py --headless -u 5 -r 2 --run-time 10s --host http://localhost:8000
```

### 3. Running with Locust Web UI
To run an interactive test with real-time latency graphs:

```bash
locust -f locustfile.py --host http://localhost:8000
```
Open `http://localhost:8089` in your browser, configure user count and spawn rate, and click **Start swarming**.

---

## Continuous Integration (GitHub Actions)

The CI pipeline is defined in `.github/workflows/ci.yml`.

### Workflow Characteristics:
- **Triggers**: Pushes to `main` and `feature/**` branches, and pull requests to `main`.
- **Least-Privilege Security**: Configured with `permissions: contents: read`.
- **Database Isolation**: Spins up an ephemeral `postgres:16-alpine` service container with built-in health checks.
- **Safe Environment**: Uses dummy secrets (`dummy_ci_groq_api_key_not_used_in_tests`) — zero exposure of production secrets or real Groq API keys.
- **Verification Steps**:
  1. Checks out repository.
  2. Sets up Python 3.13 with `pip` dependency caching.
  3. Installs dependencies from `requirements.txt`.
  4. Runs `alembic upgrade head` against the CI PostgreSQL container to validate database migrations.
  5. Executes the full `pytest` test suite.

> **Note on CI Validation:** The workflow configuration has been verified locally for YAML correctness and dependency resolution. The actual remote GitHub Actions workflow will execute automatically once changes are pushed to GitHub.

---

## Production Deployment on Render

MockMate is configured for seamless deployment on Render using an Infrastructure-as-Code Blueprint (`render.yaml`).

### Deployment Topology:
1. **`mockmate-postgres`**: Render-managed PostgreSQL database.
2. **`mockmate-backend`**: FastAPI Python Web Service (auto-connected to `mockmate-postgres`).
3. **`mockmate-frontend`**: Streamlit Python Web Service (connected to `mockmate-backend`).

### Environment Variables Reference

| Variable | Target Service | Purpose | Value / Example |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Backend | Environment flag | `production` |
| `DATABASE_URL` | Backend | PostgreSQL connection | Render database property `connectionString` |
| `GROQ_API_KEY` | Backend | Groq LLM authentication | Configured as secret in Render Dashboard |
| `GROQ_MODEL` | Backend | Model identifier | `openai/gpt-oss-120b` |
| `JWT_SECRET_KEY` | Backend | JWT signing key | Render `generateValue: true` (or custom 32+ char key) |
| `JWT_ALGORITHM` | Backend | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | Token TTL | `30` |
| `RATE_LIMIT_ENABLED` | Backend | SlowAPI rate limiting | `true` |
| `CORS_ORIGINS` | Backend | Allowed CORS origins | `https://mockmate-frontend.onrender.com,http://localhost:8501` |
| `MOCKMATE_API_URL` | Frontend | Backend API endpoint | `https://mockmate-backend.onrender.com` |

---

### Step-by-Step Render Dashboard Deployment Guide

#### Step 1: Push Code to GitHub
Ensure the latest code on `feature/deployment-cicd` (or merged `main`) is pushed to your GitHub repository:
```bash
git push origin <your-branch>
```

#### Step 2: Create Blueprint Instance on Render
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation and select **Blueprint**.
3. Connect your GitHub account and select the **`AbHaq24/MockMate`** repository.
4. Select the target branch (`feature/deployment-cicd` or `main`).
5. Render will automatically detect and parse `render.yaml`.

#### Step 3: Configure Required Secrets
Render will prompt you for any environment variables marked with `sync: false`:
1. Enter your **`GROQ_API_KEY`** in the prompt (starts with `gsk_...`).
2. Verify that `JWT_SECRET_KEY` is set to auto-generate or provide a secure key.

#### Step 4: Verify Service Names & URLs
- Render generates default URLs in the form:
  - Frontend: `https://mockmate-frontend.onrender.com` (or `<service-name>.onrender.com`)
  - Backend: `https://mockmate-backend.onrender.com` (or `<service-name>.onrender.com`)
- If your assigned domain names differ due to name collisions:
  1. In the **`mockmate-frontend`** settings, update `MOCKMATE_API_URL` to point to your actual backend URL: `https://<your-backend-service>.onrender.com`.
  2. In the **`mockmate-backend`** settings, update `CORS_ORIGINS` to include your actual frontend URL: `https://<your-frontend-service>.onrender.com`.

#### Step 5: Deploy & Monitor
1. Click **Apply** to provision the database and deploy both web services.
2. In the backend deployment logs, verify that:
   - `pip install -r requirements.txt && alembic upgrade head` completes successfully.
   - Uvicorn starts on `0.0.0.0:$PORT`.
   - `/health` responds with HTTP 200 `{"status": "healthy"}`.
3. In the frontend deployment logs, verify that Streamlit launches on port `$PORT`.
4. Navigate to your frontend URL to begin conducting mock interviews!

---

## License & Contributing
This project is developed for educational and portfolio demonstration. Contributions, issues, and feature requests are welcome!
