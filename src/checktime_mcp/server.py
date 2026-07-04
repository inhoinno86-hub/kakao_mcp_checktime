from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .tools import TOOL_REGISTRY, handle_tool


def read_payload(input_path: str | None) -> dict[str, Any]:
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw)
    if "input" in payload and isinstance(payload["input"], dict):
        return payload["input"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Local tool runner for checktime MCP")
    parser.add_argument("tool", choices=sorted(TOOL_REGISTRY))
    parser.add_argument("--input", dest="input_path")
    args = parser.parse_args()

    response = handle_tool(args.tool, read_payload(args.input_path))
    json.dump(response, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
