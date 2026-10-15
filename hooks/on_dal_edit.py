#!/usr/bin/env python3
"""
on_dal_edit.py — run the tenancy and async checks on code that just changed.

Event:   PostToolUse on Edit, Write
Calls:   .claude/hooks/_hook.py
         .claude/scripts/dal_guard.py
Rules:   .claude/skills/dal-conventions.md
         .claude/skills/service-conventions.md

A missing tenant filter is a data leak between customers. It does not look
like a bug — the endpoint works, the tests pass, and one tenant can read
another's records. This hook catches the mechanical cases at the moment the
code is written.

It is a lint, not a proof. dal_guard.py reasons about names, so it misses
indirection and occasionally flags something fine. The security-reviewer
subagent covers what it cannot.

Auth files additionally get flagged for review: any change under app/auth/
triggers the security-reviewer, every time, no batching to story end. A bad
pattern in ordinary CRUD is a bug you fix; a bad pattern in auth is an
unlocked door nobody notices.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

TIMEOUT = 30
WATCHED = ("app/dal", "app/services", "app/api", "app/auth")


def main() -> None:
    event = _hook.read_event()
    path = _hook.file_path(event)

    if not path or not path.endswith(".py"):
        _hook.allow()
    if not _hook.under(path, *WATCHED):
        _hook.allow()
    if not Path(path).is_file():
        _hook.allow()

    root = _hook.project_root()
    script = root / ".claude" / "scripts" / "dal_guard.py"
    if not script.is_file():
        _hook.allow()

    rel = _hook.relative(path)

    try:
        proc = subprocess.run(
            [sys.executable, str(script), rel, "--quiet"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        _hook.allow()

    output = ((proc.stdout or "") + (proc.stderr or "")).strip()

    if _hook.under(path, "app/auth"):
        _hook.note(
            f"{rel} is auth code. Run the security-reviewer on this change "
            "before continuing — every change under app/auth/ is reviewed, "
            "no exceptions. See .claude/agents/security-reviewer.md"
        )

    if proc.returncode > 0 and output:
        _hook.block(
            f"Invariant check failed on {rel}:\n\n{output}",
            fix=(
                "every query on a tenant-scoped table filters on tenant and "
                "excludes soft-deleted rows — these are not optional"
            ),
            skill="dal-conventions",
        )

    _hook.allow()


_hook.run(main)
