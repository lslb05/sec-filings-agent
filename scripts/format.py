"""Formats and applies automatic lint fixes.

uv run python scripts/format.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("format", ("ruff", "format", ".")),
    ("lint --fix", ("ruff", "check", "--fix", ".")),
)


def main() -> int:
    if shutil.which("ruff") is None:
        print(
            "error: ruff not found on PATH.\n"
            "Run 'uv sync' and call this script with "
            "'uv run python scripts/format.py'.",
            file=sys.stderr,
        )
        return 127

    for name, cmd in STEPS:
        print(f"==> {name}: {' '.join(cmd)}", flush=True)
        code = subprocess.run(cmd, cwd=ROOT).returncode
        if code != 0:
            print(f"error: step '{name}' failed with code {code}", file=sys.stderr)
            return code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
