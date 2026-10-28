

import sys
from pathlib import Path

# Ensure the repository root is importable in CI and local test runs.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.limiter import limiter


def pytest_configure():
    limiter.enabled = False

