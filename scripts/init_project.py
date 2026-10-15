#!/usr/bin/env python3
"""
init_project.py — copy the toolkit's project template into a new project root.

Called by:  .claude/commands/init-project.md
Calls:      nothing
Reads:      .claude/project-template/
Writes:     <project root>/  (CLAUDE.md, README.md, .env.example,
            conventions.override.md, .gitignore, plan/, contracts/)

Run once, at project start. Refuses to overwrite anything that already exists.
Stdlib only — this runs before the project's Poetry environment exists.

Usage:
    python .claude/scripts/init_project.py [--name "Project Name"] [--dry-run]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATE_DIRNAME = "project-template"
GITIGNORE_SOURCE = "gitignore.template"
GITIGNORE_TARGET = ".gitignore"
PLACEHOLDER = "<PROJECT NAME>"


def find_paths() -> tuple[Path, Path]:
    """Return (toolkit_root, project_root) based on this file's location.

    This script lives at <project>/.claude/scripts/init_project.py, so the
    toolkit root is two levels up and the project root is three.
    """
    here = Path(__file__).resolve()
    toolkit_root = here.parent.parent
    project_root = toolkit_root.parent

    template = toolkit_root / TEMPLATE_DIRNAME
    if not template.is_dir():
        fail(
            f"No {TEMPLATE_DIRNAME}/ found at {template}.\n"
            "Expected this script to live at <project>/.claude/scripts/."
        )
    return toolkit_root, project_root


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def collect(template: Path) -> list[tuple[Path, Path]]:
    """Return (source, relative_destination) for every file to copy."""
    pairs: list[tuple[Path, Path]] = []
    for src in sorted(template.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(template)
        if rel.name == GITIGNORE_SOURCE:
            rel = rel.with_name(GITIGNORE_TARGET)
        pairs.append((src, rel))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", help="Project name; replaces the placeholder")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen, change nothing"
    )
    args = parser.parse_args()

    toolkit_root, project_root = find_paths()
    template = toolkit_root / TEMPLATE_DIRNAME

    pairs = collect(template)
    if not pairs:
        fail(f"{template} is empty.")

    # Refuse to clobber. Partial init is worse than no init.
    existing = [rel for _, rel in pairs if (project_root / rel).exists()]
    if existing:
        print("Refusing to overwrite existing files:\n", file=sys.stderr)
        for rel in existing:
            print(f"  {rel}", file=sys.stderr)
        print(
            "\nThis project looks already initialised. Remove these files first "
            "if you really mean to re-run init.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print(f"Would copy {len(pairs)} files into {project_root}:\n")
        for _, rel in pairs:
            print(f"  {rel}")
        if args.name:
            print(f'\nWould replace "{PLACEHOLDER}" with "{args.name}".')
        return 0

    copied = 0
    renamed_placeholder = 0
    for src, rel in pairs:
        dest = project_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if rel.name == ".gitkeep":
            dest.write_text("", encoding="utf-8")
            copied += 1
            continue

        shutil.copy2(src, dest)
        copied += 1

        if args.name:
            try:
                text = dest.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if PLACEHOLDER in text:
                dest.write_text(text.replace(PLACEHOLDER, args.name), encoding="utf-8")
                renamed_placeholder += 1

    print(f"Copied {copied} files into {project_root}")
    if args.name:
        print(f'Replaced the project-name placeholder in {renamed_placeholder} files')
    else:
        print(f'No --name given; "{PLACEHOLDER}" is still in CLAUDE.md and README.md')

    print(
        "\nNext:\n"
        "  1. Fill in CLAUDE.md (one line on what this service does)\n"
        "  2. cp .env.example .env  and set real values\n"
        "  3. poetry init / poetry install\n"
        "  4. /ingest-requirements <path-to-document>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
