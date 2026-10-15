#!/usr/bin/env python3
"""
guard_env.py — block any read or write of .env files.

Event:   PreToolUse on Read, Edit, Write
Calls:   .claude/hooks/_hook.py
Rule:    .claude/skills/... (invariant, see CLAUDE-base.md)

.env holds real secrets. Claude never reads it and never writes it.
.env.example is the committed contract — every key present, placeholders only.

This duplicates the settings.json deny list on purpose. The deny list is the
hard stop; this hook exists to give a useful message instead of a bare refusal.

Fails CLOSED on an unreadable path: if the event names something this hook
cannot resolve but the raw text mentions .env, it blocks. The cost of a false
block here is one rephrased request; the cost of a miss is a leaked secret.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

ALLOWED = {".env.example", ".env.template", ".env.sample"}


def is_env_file(name: str) -> bool:
    if not name:
        return False
    if name in ALLOWED:
        return False
    return name == ".env" or name.startswith(".env.")


def main() -> None:
    event = _hook.read_event()
    path = _hook.file_path(event)
    name = Path(path).name if path else ""

    if is_env_file(name):
        _hook.block(
            f"Blocked: {name} holds real secrets and is never read or written "
            "by Claude.",
            fix=(
                "edit .env.example instead, with a placeholder value, and tell "
                "the user which key to set in their own .env"
            ),
        )

    _hook.allow()


_hook.run(main)
