#!/usr/bin/env python3
"""
on_plan_edit.py — regenerate derived views and check plan integrity.

Event:   PostToolUse on Edit, Write
Calls:   .claude/hooks/_hook.py
         .claude/scripts/regen_indexes.py
         .claude/scripts/check_links.py
Rule:    .claude/skills/plan-file-format.md

Plan files declare their PARENTS only. Every downward view — phase to
stories, story to endpoints, requirement to implementations — is derived.
This hook regenerates them the moment a plan file changes, so a child list
can never drift out of date.

It also rolls status up: endpoints own their status, stories and phases
derive theirs.

Integrity errors are reported back. A dangling reference caught now costs
one correction; caught three weeks later it costs an investigation.

Edits to plan/generated/ are blocked outright — those files are output, and
hand-editing one is silently undone by the next regeneration.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

TIMEOUT = 30


def run_script(root: Path, name: str, *args: str) -> tuple[int, str]:
    script = root / ".claude" / "scripts" / name
    if not script.is_file():
        return -1, ""
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1, ""
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> None:
    event = _hook.read_event()
    path = _hook.file_path(event)

    if not path or not _hook.under(path, "plan"):
        _hook.allow()

    if _hook.under(path, "plan/generated"):
        _hook.block(
            "Blocked: plan/generated/ is derived output, not a source of truth. "
            "Any edit here is overwritten by the next regeneration.",
            fix=(
                "change the plan file that declares the link — children are "
                "never listed by hand"
            ),
            skill="plan-file-format",
        )

    root = _hook.project_root()

    code, output = run_script(root, "regen_indexes.py", "--quiet")
    if code == -1:
        _hook.allow()  # script missing or environment not ready

    code, output = run_script(root, "check_links.py", "--quiet")
    if code > 0 and output.strip():
        _hook.block(
            "Plan integrity check failed after this edit:\n\n" + output.strip(),
            fix="fix the reference, or mark the requirement deferred",
            skill="plan-file-format",
        )

    _hook.allow()


_hook.run(main)
