#!/usr/bin/env python3
"""
_plan.py — shared helpers for reading the plan/ directory.

Called by:  .claude/scripts/id_allocator.py
            .claude/scripts/check_links.py
            .claude/scripts/regen_indexes.py
            .claude/scripts/trace_impact.py
Calls:      nothing

Stdlib only. These helpers run from hooks, which execute outside the
project's Poetry environment and cannot import third-party packages.

The frontmatter format is deliberately flat — see
.claude/skills/plan-file-format.md. One `key: value` per line, lists
bracketed and comma-separated, no nesting. That is what makes a
thirty-line parser sufficient.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# ID patterns
# --------------------------------------------------------------------------

ID_PATTERNS = {
    "REQ": re.compile(r"^REQ-\d{3,}$"),
    "PH": re.compile(r"^PH-\d+$"),
    "US": re.compile(r"^US-\d{3,}$"),
    "EP": re.compile(r"^EP-\d{3,}$"),
    "DEC": re.compile(r"^DEC-\d{3,}$"),
    "Q": re.compile(r"^Q-\d{3,}$"),
    "CR": re.compile(r"^CR-\d{3,}$"),
    "ERR": re.compile(r"^ERR-\d{3,}$"),
}

# Width used when minting a new ID. PH is deliberately unpadded.
ID_WIDTH = {
    "REQ": 3, "US": 3, "EP": 3, "DEC": 3,
    "Q": 3, "CR": 3, "ERR": 3, "PH": 0,
}

ANY_ID = re.compile(r"\b(REQ|PH|US|EP|DEC|Q|CR|ERR)-\d+\b")

# Entries in the flat multi-entry files are delimited by a heading.
HEADING_ID = re.compile(r"^###\s+([A-Z]+-\d+)\s*$", re.MULTILINE)

# Files that are templates, not real plan entries.
TEMPLATE_NAMES = {"_template.md"}

REQUIRED_KEYS = {
    "phase": ["id", "type", "status", "name"],
    "story": ["id", "type", "phase", "requirements", "status", "questions", "name"],
    "endpoint": [
        "id", "type", "story", "requirements", "status", "method", "path",
        "contract", "permission", "tenant_scoped", "idempotency_key",
        "errors", "decisions", "questions",
    ],
    "change-request": [
        "id", "type", "date", "requirement", "status", "classification",
        "stories", "endpoints", "contracts", "decisions",
    ],
}

ENDPOINT_STATUSES = {
    "planned", "contracted", "tests-written", "building", "done", "needs-rebuild",
}


# --------------------------------------------------------------------------
# Frontmatter
# --------------------------------------------------------------------------

class FrontmatterError(Exception):
    """Raised when a plan file's frontmatter cannot be parsed."""


def parse_frontmatter(text: str) -> dict[str, object]:
    """Parse flat YAML-ish frontmatter into a dict.

    Values are returned as str, bool, or list[str]. Anything the flat
    format does not support raises FrontmatterError rather than being
    silently mangled.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file does not start with '---'")

    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter is not closed with '---'") from None

    data: dict[str, object] = {}
    for lineno, raw in enumerate(lines[1:end], start=2):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            raise FrontmatterError(
                f"line {lineno}: indentation is not supported — the format is flat"
            )
        if ":" not in line:
            raise FrontmatterError(f"line {lineno}: expected 'key: value'")

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if not key:
            raise FrontmatterError(f"line {lineno}: empty key")
        if key in data:
            raise FrontmatterError(f"line {lineno}: duplicate key '{key}'")

        data[key] = _coerce(value)

    return data


def _coerce(value: str) -> object:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [p.strip() for p in inner.split(",") if p.strip()]
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    return value


# --------------------------------------------------------------------------
# Plan model
# --------------------------------------------------------------------------

@dataclass
class PlanFile:
    path: Path
    kind: str                       # phase | story | endpoint | change-request
    data: dict[str, object]
    body: str
    errors: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.data.get("id", ""))

    def get_list(self, key: str) -> list[str]:
        value = self.data.get(key, [])
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)] if value else []

    def get_str(self, key: str) -> str:
        value = self.data.get(key, "")
        return "" if isinstance(value, list) else str(value)


@dataclass
class Plan:
    root: Path                      # the project root
    phases: dict[str, PlanFile] = field(default_factory=dict)
    stories: dict[str, PlanFile] = field(default_factory=dict)
    endpoints: dict[str, PlanFile] = field(default_factory=dict)
    changes: dict[str, PlanFile] = field(default_factory=dict)
    requirements: dict[str, str] = field(default_factory=dict)   # id -> status
    questions: dict[str, str] = field(default_factory=dict)
    decisions: set[str] = field(default_factory=set)
    errors: dict[str, str] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def plan_dir(self) -> Path:
        return self.root / "plan"

    def all_leaves(self) -> list[PlanFile]:
        return [
            *self.phases.values(),
            *self.stories.values(),
            *self.endpoints.values(),
            *self.changes.values(),
        ]

    def known_ids(self) -> set[str]:
        return (
            set(self.phases)
            | set(self.stories)
            | set(self.endpoints)
            | set(self.changes)
            | set(self.requirements)
            | set(self.questions)
            | set(self.decisions)
            | set(self.errors)
        )


LEAF_DIRS = {
    "phases": "phase",
    "stories": "story",
    "endpoints": "endpoint",
    "changes": "change-request",
}


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from this script to the project root (the parent of .claude/).

    Falls back to searching upward for a directory containing plan/, so the
    scripts also work when run from a subdirectory.
    """
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if candidate.name == ".claude":
            return candidate.parent
    for candidate in [here, *here.parents]:
        if (candidate / "plan").is_dir():
            return candidate
    raise SystemExit("ERROR: could not locate the project root (no .claude/ or plan/)")


def load_plan(root: Path | None = None) -> Plan:
    """Read every plan file. Parse failures become problems, not exceptions."""
    root = root or find_project_root()
    plan = Plan(root=root)

    if not plan.plan_dir.is_dir():
        plan.problems.append(f"no plan/ directory at {plan.plan_dir}")
        return plan

    for dirname, kind in LEAF_DIRS.items():
        target = {
            "phase": plan.phases,
            "story": plan.stories,
            "endpoint": plan.endpoints,
            "change-request": plan.changes,
        }[kind]

        folder = plan.plan_dir / dirname
        if not folder.is_dir():
            continue

        for path in sorted(folder.glob("*.md")):
            if path.name in TEMPLATE_NAMES:
                continue
            rel = path.relative_to(root)
            text = path.read_text(encoding="utf-8")
            try:
                data = parse_frontmatter(text)
            except FrontmatterError as exc:
                plan.problems.append(f"{rel}: {exc}")
                continue

            pf = PlanFile(path=path, kind=kind, data=data, body=text)

            for key in REQUIRED_KEYS[kind]:
                if key not in data:
                    pf.errors.append(f"missing required key '{key}'")

            if not pf.id:
                plan.problems.append(f"{rel}: frontmatter has no id")
                continue
            if pf.id in target:
                plan.problems.append(
                    f"{rel}: duplicate id {pf.id} "
                    f"(also {target[pf.id].path.relative_to(root)})"
                )
                continue
            if data.get("type") != kind:
                pf.errors.append(f"type is '{data.get('type')}', expected '{kind}'")

            target[pf.id] = pf

    plan.requirements = _load_statused(plan.plan_dir / "requirements" / "inventory.md")
    plan.questions = _load_statused(plan.plan_dir / "questions.md")
    plan.errors = _load_statused(plan.plan_dir / "errors.md")
    plan.decisions = set(_load_statused(plan.plan_dir / "decisions.md"))

    return plan


def _load_statused(path: Path) -> dict[str, str]:
    """Read `### ID` entries from a flat multi-entry file, with their status."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    found: dict[str, str] = {}
    matches = list(HEADING_ID.finditer(text))
    for i, match in enumerate(matches):
        entry_id = match.group(1)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[match.end():end]
        status_match = re.search(
            r"^\*\*Status:\*\*\s*(\S+)", chunk, re.MULTILINE
        )
        found[entry_id] = status_match.group(1).lower() if status_match else "unknown"
    return found


def referenced_ids(text: str) -> set[str]:
    """Every ID-shaped token in a string. Used for loose reference checks."""
    return {m.group(0) for m in ANY_ID.finditer(text)}


def valid_id(value: str) -> bool:
    prefix = value.split("-", 1)[0]
    pattern = ID_PATTERNS.get(prefix)
    return bool(pattern and pattern.match(value))
