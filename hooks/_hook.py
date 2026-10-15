#!/usr/bin/env python3
"""
_hook.py — shared protocol helper for every hook in this directory.

Called by:  every file in .claude/hooks/
Calls:      nothing

Stdlib only. Hooks run outside the project's Poetry environment.

WHY THIS FILE EXISTS
--------------------
Claude Code pipes a JSON event to a hook on stdin and reads the hook's exit
code to decide what happens next. The exact key names in that event, and the
exact signalling convention, change between releases.

Every hook therefore goes through this module. If the protocol turns out to
differ from what is assumed here, there is one file to correct rather than
seven.

VERIFYING THE PROTOCOL
----------------------
Run any hook with --probe to see the real event shape:

    echo '{}' | python .claude/hooks/_hook.py --probe

Then trigger a real hook and look at what Claude Code actually sends. If the
key names differ, fix FILE_KEYS / COMMAND_KEYS / TOOL_KEYS below.

FAIL-OPEN BY DESIGN
-------------------
If the event cannot be parsed, hooks allow the action. A hook that misfires
and blocks every edit makes the toolkit unusable at exactly the moment you
are trying to work. A hook that silently stops enforcing is recoverable —
check_links.py, dal_guard.py and the security-reviewer still catch things.

Fail closed only where the cost of being wrong is a leaked secret or lost
data; those cases call block_on_error() explicitly.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Exit codes. ALLOW lets the action proceed; BLOCK stops it and shows the
# message on stderr to Claude.
ALLOW = 0
BLOCK = 2

# Candidate key names, most likely first. Checked in order.
FILE_KEYS = ("file_path", "filePath", "path", "file", "target_file")
COMMAND_KEYS = ("command", "cmd", "bash_command", "script")
TOOL_KEYS = ("tool_name", "toolName", "tool", "name")
INPUT_KEYS = ("tool_input", "toolInput", "input", "params", "arguments")

DEBUG = os.environ.get("CLAUDE_HOOK_DEBUG") == "1"


# --------------------------------------------------------------------------
# Reading the event
# --------------------------------------------------------------------------

def read_event() -> dict[str, Any]:
    """Parse the JSON event from stdin. Returns {} if anything goes wrong."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        if DEBUG:
            print(f"[hook] could not parse stdin: {raw[:200]}", file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _dig(event: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Find the first matching key, at the top level or one level in."""
    for key in keys:
        if key in event and event[key] not in (None, ""):
            return event[key]

    for container_key in INPUT_KEYS:
        inner = event.get(container_key)
        if isinstance(inner, dict):
            for key in keys:
                if key in inner and inner[key] not in (None, ""):
                    return inner[key]
    return None


def tool_name(event: dict[str, Any]) -> str:
    value = _dig(event, TOOL_KEYS)
    return str(value) if value else ""


def file_path(event: dict[str, Any]) -> str:
    value = _dig(event, FILE_KEYS)
    return str(value) if value else ""


def command(event: dict[str, Any]) -> str:
    value = _dig(event, COMMAND_KEYS)
    return str(value) if value else ""


def content(event: dict[str, Any]) -> str:
    """New file content or replacement text, when the event carries it."""
    parts: list[str] = []
    for key in ("new_string", "newString", "content", "new_str", "text"):
        value = _dig(event, (key,))
        if value:
            parts.append(str(value))
    return "\n".join(parts)


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

def project_root() -> Path:
    """The project root — the parent of .claude/."""
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if candidate.name == ".claude":
            return candidate.parent
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path.cwd()


def relative(path_str: str) -> str:
    """Project-relative path with forward slashes. Falls back to the input."""
    if not path_str:
        return ""
    try:
        path = Path(path_str).resolve()
        return str(path.relative_to(project_root())).replace("\\", "/")
    except (ValueError, OSError):
        return path_str.replace("\\", "/")


def under(path_str: str, *folders: str) -> bool:
    """True if the path sits inside any of the given project folders."""
    rel = relative(path_str)
    return any(rel == f or rel.startswith(f.rstrip("/") + "/") for f in folders)


def matches_name(path_str: str, *names: str) -> bool:
    name = Path(path_str).name if path_str else ""
    return name in names


# --------------------------------------------------------------------------
# Signalling
# --------------------------------------------------------------------------

def block(reason: str, *, fix: str = "", skill: str = "") -> None:
    """Stop the action and tell Claude why. Never returns."""
    lines = [reason]
    if fix:
        lines.append(f"Instead: {fix}")
    if skill:
        lines.append(f"See .claude/skills/{skill}.md")
    print("\n".join(lines), file=sys.stderr)
    sys.exit(BLOCK)


def allow() -> None:
    """Let the action proceed. Never returns."""
    sys.exit(ALLOW)


def note(message: str) -> None:
    """Surface information without blocking."""
    print(message, file=sys.stderr)


def run(main_fn) -> None:
    """Wrap a hook's logic so an unexpected error fails open.

    A crashing hook must not become a wall between the user and their work.
    """
    try:
        main_fn()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — deliberate catch-all
        if DEBUG:
            print(f"[hook] {Path(sys.argv[0]).name} failed: {exc}", file=sys.stderr)
        sys.exit(ALLOW)
    sys.exit(ALLOW)


# --------------------------------------------------------------------------
# Probe
# --------------------------------------------------------------------------

def _probe() -> None:
    raw = sys.stdin.read()
    print("--- raw stdin ---")
    print(raw or "(empty)")
    print("\n--- parsed ---")
    try:
        event = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        print(f"not JSON: {exc}")
        return
    print(json.dumps(event, indent=2))
    print("\n--- what the helpers extract ---")
    print(f"tool_name : {tool_name(event)!r}")
    print(f"file_path : {file_path(event)!r}")
    print(f"command   : {command(event)!r}")
    print(f"root      : {project_root()}")
    print(
        "\nIf any of these are empty but should not be, "
        "fix FILE_KEYS / COMMAND_KEYS / TOOL_KEYS in this file."
    )


if __name__ == "__main__":
    if "--probe" in sys.argv:
        _probe()
    else:
        print(__doc__)
    sys.exit(ALLOW)
