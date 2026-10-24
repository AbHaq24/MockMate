
import pytest

from backend.limiter import limiter


@pytest.fixture(autouse=True)
def disable_rate_limiting_during_tests():
    original_enabled = limiter.enabled
    limiter.enabled = False

    yield

    limiter.enabled = original_enabled
