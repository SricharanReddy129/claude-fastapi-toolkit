#!/usr/bin/env python3
"""
id_allocator.py — mint the next unused ID of a given type.

Called by:  .claude/commands/ingest-requirements.md
            .claude/commands/plan-phases.md
            .claude/commands/plan-story.md
            .claude/commands/change-request.md
            .claude/commands/new-requirement.md
            .claude/commands/add-error-code.md
Calls:      .claude/scripts/_plan.py

Stdlib only.

IDs are permanent and never reused — see .claude/skills/plan-file-format.md.
This script therefore allocates strictly above the highest ID ever seen,
including ones belonging to removed or deferred items. It never fills a gap.

Usage:
    python .claude/scripts/id_allocator.py EP
    python .claude/scripts/id_allocator.py REQ --count 5
    python .claude/scripts/id_allocator.py --list
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _plan import (  # noqa: E402
    ID_PATTERNS,
    ID_WIDTH,
    find_project_root,
    load_plan,
)

# Where each ID type lives, for scanning purposes.
SOURCES = {
    "REQ": [("requirements",)],
    "PH": [("phases",)],
    "US": [("stories",)],
    "EP": [("endpoints",)],
    "CR": [("changes",)],
    "DEC": [("decisions",)],
    "Q": [("questions",)],
    "ERR": [("errors",)],
}


def highest_seen(root: Path, prefix: str) -> int:
    """Highest numeric suffix for this prefix anywhere under plan/.

    Scans the raw text of every plan file rather than only parsed IDs, so an
    ID mentioned in a changelog or a removed entry still counts. Reusing an
    ID would silently repoint historical references.
    """
    pattern = re.compile(rf"\b{prefix}-(\d+)\b")
    highest = 0
    plan_dir = root / "plan"
    if not plan_dir.is_dir():
        return 0

    for path in plan_dir.rglob("*.md"):
        if path.name == "_template.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in pattern.finditer(text):
            highest = max(highest, int(match.group(1)))

    # Contracts reference endpoint and error IDs too.
    contracts = root / "contracts"
    if contracts.is_dir() and prefix in ("EP", "ERR"):
        for path in contracts.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for match in pattern.finditer(text):
                highest = max(highest, int(match.group(1)))

    return highest


def format_id(prefix: str, number: int) -> str:
    width = ID_WIDTH.get(prefix, 3)
    return f"{prefix}-{number:0{width}d}" if width else f"{prefix}-{number}"


def list_all(root: Path) -> int:
    plan = load_plan(root)
    rows = [
        ("REQ", len(plan.requirements)),
        ("PH", len(plan.phases)),
        ("US", len(plan.stories)),
        ("EP", len(plan.endpoints)),
        ("CR", len(plan.changes)),
        ("DEC", len(plan.decisions)),
        ("Q", len(plan.questions)),
        ("ERR", len(plan.errors)),
    ]
    print(f"{'type':<6}{'count':>7}{'next':>12}")
    for prefix, count in rows:
        nxt = format_id(prefix, highest_seen(root, prefix) + 1)
        print(f"{prefix:<6}{count:>7}{nxt:>12}")

    if plan.problems:
        print(f"\n{len(plan.problems)} problem(s) found — run check_links.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prefix", nargs="?", choices=sorted(ID_PATTERNS), help="ID type to allocate"
    )
    parser.add_argument("--count", type=int, default=1, help="how many to mint")
    parser.add_argument(
        "--list", action="store_true", help="show counts and next ID for every type"
    )
    args = parser.parse_args()

    root = find_project_root()

    if args.list:
        return list_all(root)

    if not args.prefix:
        parser.error("give an ID type, or use --list")
    if args.count < 1:
        parser.error("--count must be at least 1")

    start = highest_seen(root, args.prefix) + 1
    for n in range(start, start + args.count):
        print(format_id(args.prefix, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
