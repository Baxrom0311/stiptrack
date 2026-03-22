from __future__ import annotations

from pathlib import Path
import re


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ALLOWED_RAW_SQL_LINES = {
    Path("api/v1/health.py"): {
        'await session.execute(text("SELECT 1"))',
    }
}
RAW_SQL_PATTERNS = (
    re.compile(r"\btext\("),
    re.compile(r"\bfrom_statement\("),
    re.compile(r"\bliteral_column\("),
    re.compile(r"\.execute\(\s*[\"']"),
)


def test_backend_avoids_raw_sql_outside_healthcheck():
    violations: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        rel_path = path.relative_to(APP_ROOT)
        allowed_lines = ALLOWED_RAW_SQL_LINES.get(rel_path, set())

        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped in allowed_lines:
                continue

            if any(pattern.search(line) for pattern in RAW_SQL_PATTERNS):
                violations.append(f"{rel_path}:{lineno}:{stripped}")

    assert not violations, "Raw SQL usage topildi:\n" + "\n".join(violations)
