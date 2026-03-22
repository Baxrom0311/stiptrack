from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits(request: pytest.FixtureRequest):
    original_enabled = limiter.enabled
    limiter.enabled = request.node.path.name == "test_rate_limit.py"
    limiter.reset()
    yield
    limiter.enabled = original_enabled
    limiter.reset()
