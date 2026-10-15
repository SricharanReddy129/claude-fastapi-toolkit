#!/usr/bin/env python3
"""
guard_test_db.py — protect the shared database and applied migrations.

Event:   PreToolUse on Edit, Write
Calls:   .claude/hooks/_hook.py
Rules:   .claude/skills/testing-strategy.md
         .claude/skills/alembic-migrations.md

This project runs dev and tests against ONE database. Isolation comes from
the session fixture opening a transaction and rolling it back
unconditionally. That only holds while three rules hold:

  no test commits · no test truncates or drops · tests create their own data

A single `TRUNCATE` in a test file deletes real development data on the next
run. This hook is the mechanical half of that guarantee.

It also blocks edits to migrations that have already been applied. Once
applied anywhere, a migration is immutable — fix forward with a new revision.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _hook  # noqa: E402

DESTRUCTIVE = [
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE"),
    (re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE), "DROP"),
    (re.compile(r"\bdrop_all\s*\(", re.IGNORECASE), "metadata.drop_all()"),
    (re.compile(r"\bDELETE\s+FROM\s+\w+\s*(?:;|$)", re.IGNORECASE),
     "unfiltered DELETE FROM"),
]

COMMIT = re.compile(r"\b(session|db|conn)\s*\.\s*commit\s*\(", re.IGNORECASE)

# A migration carries a revision identifier; a down_revision pointing at a
# real revision means it sits in an applied chain.
HAS_REVISION = re.compile(r"^revision(?:\s*:\s*str)?\s*=", re.MULTILINE)


def check_tests(path: str, text: str) -> None:
    if not _hook.under(path, "tests"):
        return
    if not text:
        return

    for pattern, label in DESTRUCTIVE:
        if pattern.search(text):
            _hook.block(
                f"Blocked: {label} in a test file. Dev and tests share one "
                "database — this deletes real development data.",
                fix=(
                    "let the session fixture roll back; tests create their "
                    "own data inside the transaction"
                ),
                skill="testing-strategy",
            )

    if COMMIT.search(text):
        _hook.block(
            "Blocked: a test that commits escapes the rollback and writes to "
            "the shared database.",
            fix=(
                "the fixture owns the transaction — never commit in a test, "
                "and have services take an injected session"
            ),
            skill="testing-strategy",
        )


def check_migration(path: str) -> None:
    if not _hook.under(path, "alembic/versions"):
        return

    target = Path(path)
    if not target.is_file():
        return  # new revision being written — fine

    try:
        existing = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    if HAS_REVISION.search(existing):
        _hook.block(
            f"Blocked: {target.name} is an existing migration. Once applied, "
            "a migration is immutable.",
            fix=(
                "create a new revision that fixes forward, with a working "
                "downgrade"
            ),
            skill="alembic-migrations",
        )


def check_test_config(path: str, text: str) -> None:
    """A test fixture must not be pointed at an unexpected database."""
    if not _hook.under(path, "tests"):
        return
    if not text:
        return
    for match in re.finditer(
        r"(?:DATABASE_URL|database_url)\s*=\s*[\"']([^\"']+)[\"']", text
    ):
        url = match.group(1)
        if any(host in url for host in ("prod", "production", "staging")):
            _hook.block(
                f"Blocked: test configuration points at '{url}'.",
                fix="tests run against the local database only",
                skill="testing-strategy",
            )


def main() -> None:
    event = _hook.read_event()
    path = _hook.file_path(event)
    if not path:
        _hook.allow()

    text = _hook.content(event)

    check_migration(path)
    check_tests(path, text)
    check_test_config(path, text)

    _hook.allow()


_hook.run(main)
