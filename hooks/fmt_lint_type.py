#!/usr/bin/env python3
"""
fmt_lint_type.py — format, lint and type-check the file that was just edited.

Event:   PostToolUse on Edit, Write
Calls:   .claude/hooks/_hook.py, and shells out to poetry run ruff / mypy

SCOPED TO THE EDITED FILE, DELIBERATELY
---------------------------------------
Pre-existing errors elsewhere never block. Otherwise one legacy module makes
the whole toolkit unusable, and the first thing anyone does is switch the
hooks off.

Formatting is applied silently. Lint and type errors in the edited file are
reported back so Claude fixes them in the same turn rather than leaving them
for later.

Reporting uses the block channel because that is how a message reaches
Claude — the edit has already happened, so nothing is undone. If a tool is
missing or the project environment is not set up, this hook stays silent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

TIMEOUT = 45
SKIP_DIRS = ("alembic/versions", ".venv", "venv", "node_modules")


def run(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return -1, ""
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> None:
    event = _hook.read_event()
    path = _hook.file_path(event)

    if not path or not path.endswith(".py"):
        _hook.allow()
    if _hook.under(path, *SKIP_DIRS):
        _hook.allow()
    if not Path(path).is_file():
        _hook.allow()

    root = _hook.project_root()
    if not (root / "pyproject.toml").is_file():
        _hook.allow()

    rel = _hook.relative(path)

    # Format and autofix first — these change the file and rarely need
    # reporting. A missing tool returns -1 and is ignored.
    run(["poetry", "run", "ruff", "format", rel], root)
    run(["poetry", "run", "ruff", "check", "--fix", rel], root)

    problems: list[str] = []

    code, output = run(["poetry", "run", "ruff", "check", rel], root)
    if code > 0 and output.strip():
        problems.append("ruff:\n" + output.strip())

    code, output = run(["poetry", "run", "mypy", rel], root)
    if code > 0 and output.strip():
        lines = [
            line
            for line in output.strip().splitlines()
            if rel in line or line.startswith("Found")
        ]
        if lines:
            problems.append("mypy:\n" + "\n".join(lines))

    if problems:
        _hook.block(
            f"{rel} has issues after the edit:\n\n" + "\n\n".join(problems),
            fix="fix them now, in this file only — ignore errors elsewhere",
        )

    _hook.allow()


_hook.run(main)
