"""Quality gate: format, lint, types and tests.

Runs the steps in order, stops on the first failure and propagates its exit
code. Uses only the standard library so it runs the same on Windows, Linux
and CI.

    uv run python scripts/check.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("format", ("ruff", "format", "--check", ".")),
    ("lint", ("ruff", "check", ".")),
    ("types", ("mypy", "src", "tests")),
    ("test", ("pytest",)),
)


def main() -> int:
    missing = sorted({cmd[0] for _, cmd in STEPS if shutil.which(cmd[0]) is None})
    if missing:
        print(
            f"error: {', '.join(missing)} not found on PATH.\n"
            "Run 'uv sync' and call this script with 'uv run python scripts/check.py'.",
            file=sys.stderr,
        )
        return 127

    for name, cmd in STEPS:
        print(f"==> {name}: {' '.join(cmd)}", flush=True)
        code = subprocess.run(cmd, cwd=ROOT).returncode
        if code != 0:
            print(f"error: step '{name}' failed with code {code}", file=sys.stderr)
            return code

    print("==> ok: format, lint, types and test all passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
