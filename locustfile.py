import os
import uuid
from locust import HttpUser, between, task


class HealthCheckUser(HttpUser):
    """Simulates anonymous health-check traffic to benchmark server latency

    and baseline request throughput.
    """

    wait_time = between(0.1, 0.5)

    @task(1)
    def check_health(self):
        with self.client.get(
            "/health",
            name="/health [Health Check]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Unexpected health status: {data}")
            else:
                response.failure(f"HTTP {response.status_code}")


class AuthenticatedCandidateUser(HttpUser):
    """Simulates authenticated candidate traffic across safe, non-LLM endpoints.

    CRITICAL SAFETY RULE:
    Does NOT call question generation (/questions) or answer evaluation (/answer)
    endpoints to avoid flooding external LLM APIs (Groq), exhausting rate limits,
    or generating unexpected API costs during load testing.
    """

    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Register a disposable test candidate and obtain an authentication token."""
        self.test_email = f"loadtest_{uuid.uuid4().hex[:10]}@example.com"
        self.test_password = "LoadTestPassword123!"
        self.auth_headers = {}

        # 1. Register disposable test candidate
        reg_payload = {"email": self.test_email, "password": self.test_password}
        with self.client.post(
            "/auth/register",
            json=reg_payload,
            name="/auth/register [Setup]",
            catch_response=True,
        ) as reg_resp:
            if reg_resp.status_code != 201 and reg_resp.status_code != 409:
                reg_resp.failure(f"Failed to register test user: {reg_resp.text}")
                return

        # 2. Login to obtain access token
        login_payload = {"email": self.test_email, "password": self.test_password}
        with self.client.post(
            "/auth/login",
            json=login_payload,
            name="/auth/login [Setup]",
            catch_response=True,
        ) as login_resp:
            if login_resp.status_code == 200:
                token = login_resp.json().get("access_token")
                if token:
                    self.auth_headers = {"Authorization": f"Bearer {token}"}
                    login_resp.success()
                else:
                    login_resp.failure("Missing access_token in login response")
            else:
                login_resp.failure(f"Login failed: {login_resp.status_code}")

    @task(4)
    def view_profile(self):
        """Fetch current authenticated user profile."""
        if not self.auth_headers:
            return
        self.client.get(
            "/auth/me",
            headers=self.auth_headers,
            name="/auth/me [Profile]",
        )

    @task(2)
    def view_assessment_history(self):
        """Retrieve assessment history records."""
        if not self.auth_headers:
            return
        self.client.get(
            "/assessments",
            headers=self.auth_headers,
            name="/assessments [History]",
        )

    @task(2)
    def view_analytics_dashboard(self):
        """Compute aggregated candidate analytics and performance statistics."""
        if not self.auth_headers:
            return
        self.client.get(
            "/assessments/analytics",
            headers=self.auth_headers,
            name="/assessments/analytics [Analytics]",
        )

    @task(1)
    def periodic_health_check(self):
        """Periodic health verification while authenticated."""
        self.client.get(
            "/health",
            name="/health [Health Check]",
        )
