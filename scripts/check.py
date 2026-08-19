"""Portao de qualidade: formato, lint, tipos e teste.

Executa as etapas em ordem, para na primeira que falhar e propaga o codigo
de saida. Usa apenas a biblioteca padrao para rodar igual em Windows, Linux
e no CI.

    uv run python scripts/check.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("formato", ("ruff", "format", "--check", ".")),
    ("lint", ("ruff", "check", ".")),
    ("tipos", ("mypy", "src", "tests")),
    ("teste", ("pytest",)),
)


def main() -> int:
    missing = sorted({cmd[0] for _, cmd in STEPS if shutil.which(cmd[0]) is None})
    if missing:
        print(
            f"erro: {', '.join(missing)} nao encontrado no PATH.\n"
            "Rode 'uv sync' e chame este script com 'uv run python scripts/check.py'.",
            file=sys.stderr,
        )
        return 127

    for name, cmd in STEPS:
        print(f"==> {name}: {' '.join(cmd)}", flush=True)
        code = subprocess.run(cmd, cwd=ROOT).returncode
        if code != 0:
            print(f"erro: etapa '{name}' falhou com codigo {code}", file=sys.stderr)
            return code

    print("==> ok: formato, lint, tipos e teste passaram")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
