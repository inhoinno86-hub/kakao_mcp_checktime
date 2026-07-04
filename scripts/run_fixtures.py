from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checktime_mcp.tools import handle_tool  # noqa: E402


def main() -> int:
    fixture_dir = ROOT / "tests" / "fixtures"
    failures = 0
    for fixture_path in sorted(fixture_dir.glob("scenario_*.json")):
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        response = handle_tool(fixture["expected_tool"], fixture["input"])
        status = "PASS" if response.get("ok") else "FAIL"
        print(f"{status} {fixture['scenario_id']} -> {fixture['expected_tool']}")
        if not response.get("ok"):
            failures += 1
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
