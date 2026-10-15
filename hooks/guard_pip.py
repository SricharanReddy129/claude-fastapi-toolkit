#!/usr/bin/env python3
"""
guard_pip.py — block pip install; dependencies enter through Poetry only.

Event:   PreToolUse on Bash
Calls:   .claude/hooks/_hook.py
Rule:    invariant — see .claude/CLAUDE-base.md

A pip install works on this machine and leaves pyproject.toml untouched.
Six weeks later a fresh checkout fails and nobody knows which package is
missing. Everything goes through `poetry add` so the manifest and lock file
stay truthful.

Also nudges bare python/pytest/alembic/uvicorn invocations toward
`poetry run`, since running outside the environment produces confusing
import errors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

PIP_INSTALL = re.compile(
    r"(?:^|[;&|]|\s)(?:python\s+-m\s+)?pip3?\s+install\b", re.IGNORECASE
)
PIP_UNINSTALL = re.compile(
    r"(?:^|[;&|]|\s)(?:python\s+-m\s+)?pip3?\s+uninstall\b", re.IGNORECASE
)

# Commands that need the project environment.
NEEDS_POETRY = re.compile(
    r"(?:^|[;&|]\s*)\s*(pytest|alembic|uvicorn|mypy|ruff)\b", re.IGNORECASE
)
HAS_POETRY = re.compile(r"\bpoetry\s+run\b", re.IGNORECASE)


def main() -> None:
    event = _hook.read_event()
    cmd = _hook.command(event)
    if not cmd:
        _hook.allow()

    if PIP_INSTALL.search(cmd):
        _hook.block(
            "Blocked: pip install leaves pyproject.toml out of date, so a "
            "fresh checkout breaks.",
            fix="poetry add <package>   (or: poetry add --group dev <package>)",
        )

    if PIP_UNINSTALL.search(cmd):
        _hook.block(
            "Blocked: pip uninstall leaves pyproject.toml and poetry.lock "
            "disagreeing with the environment.",
            fix="poetry remove <package>",
        )

    if NEEDS_POETRY.search(cmd) and not HAS_POETRY.search(cmd):
        _hook.note(
            "Note: this runs outside the Poetry environment and will likely "
            "fail on imports. Prefix it with `poetry run`."
        )

    _hook.allow()


_hook.run(main)
