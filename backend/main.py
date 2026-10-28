import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from backend.limiter import limiter

from backend.api.auth import router as auth_router
from backend.api.assessments import router as assessments_router
from backend.config.settings import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

# Environment-configured CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_timing_headers(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.exception(
            "Request failed | method=%s | path=%s | duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Request completed | method=%s | path=%s | status=%s | duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    # Diagnostic timing header
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

    # Standard security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


app.include_router(auth_router)
app.include_router(assessments_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.environment,
    }
