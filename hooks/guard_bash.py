#!/usr/bin/env python3
"""
guard_bash.py — block destructive and out-of-scope shell commands.

Event:   PreToolUse on Bash
Calls:   .claude/hooks/_hook.py
Rule:    invariant — see .claude/CLAUDE-base.md

These are the commands whose damage cannot be undone by reading the diff:
pushing to a remote, dropping a database, recursive deletes, force-resetting
git history.

Migrations are the subtle one. `alembic upgrade` against anything but the
local database is an operational procedure, not a development action.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"(?:^|[;&|]\s*)\s*git\s+push\b", re.IGNORECASE),
        "Blocked: pushing is the user's decision, not Claude's.",
        "commit, then tell the user what is ready to push",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        "Blocked: git reset --hard discards uncommitted work irreversibly.",
        "git stash, or commit first and let the user decide",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-z]*f", re.IGNORECASE),
        "Blocked: git clean -f deletes untracked files with no recovery.",
        "list what would be removed with git clean -n and ask",
    ),
    (
        re.compile(r"\bgit\s+(checkout|restore)\s+\.", re.IGNORECASE),
        "Blocked: this discards every uncommitted change in the tree.",
        "revert specific files, or ask first",
    ),
    (
        re.compile(r"\bdropdb\b|\bDROP\s+DATABASE\b", re.IGNORECASE),
        "Blocked: dropping the database destroys development data.",
        "tests isolate by transaction rollback — nothing needs dropping",
    ),
    (
        re.compile(r"\bDROP\s+TABLE\b|\bTRUNCATE\b", re.IGNORECASE),
        "Blocked: destructive SQL outside a reviewed migration.",
        "write an Alembic migration with a working downgrade",
    ),
    (
        re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r)\b"),
        "Blocked: recursive force delete.",
        "remove specific files, or ask the user to do it",
    ),
    (
        re.compile(r"\bpoetry\s+publish\b", re.IGNORECASE),
        "Blocked: publishing is the user's decision.",
        "build locally if needed and report",
    ),
]

# Alembic upgrade is allowed only against the local database.
ALEMBIC_UPGRADE = re.compile(r"\balembic\b[^;&|]*\bupgrade\b", re.IGNORECASE)
REMOTE_HINT = re.compile(
    r"(prod|production|staging|\bDATABASE_URL=|@(?!localhost|127\.0\.0\.1))",
    re.IGNORECASE,
)


def main() -> None:
    event = _hook.read_event()
    cmd = _hook.command(event)
    if not cmd:
        _hook.allow()

    for pattern, reason, fix in RULES:
        if pattern.search(cmd):
            _hook.block(reason, fix=fix)

    if ALEMBIC_UPGRADE.search(cmd) and REMOTE_HINT.search(cmd):
        _hook.block(
            "Blocked: alembic upgrade appears to target a non-local database.",
            fix=(
                "run migrations against the local database only; deploying "
                "them is an operational procedure"
            ),
            skill="alembic-migrations",
        )

    _hook.allow()


_hook.run(main)
