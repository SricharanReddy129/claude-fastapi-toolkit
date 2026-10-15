#!/usr/bin/env python3
"""
check_links.py — verify the integrity of plan/ and of toolkit cross-references.

Called by:  hook .claude/hooks/on_plan_edit.py
            .claude/commands/verify-story.md
            .claude/commands/status.md
            .claude/commands/promote-to-toolkit.md
            .claude/commands/toolkit-status.md
Calls:      .claude/scripts/_plan.py

Stdlib only.

Exit code 0 when clean, 1 when any error is found. Warnings alone do not
fail the run.

Usage:
    python .claude/scripts/check_links.py
    python .claude/scripts/check_links.py --toolkit-only
    python .claude/scripts/check_links.py --quiet
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _plan import (  # noqa: E402
    ENDPOINT_STATUSES,
    Plan,
    find_project_root,
    load_plan,
    valid_id,
)

# A repo-relative path mentioned inside a toolkit markdown file.
TOOLKIT_PATH = re.compile(r"`?\.claude/([A-Za-z0-9_./-]+\.(?:md|py|json))`?")

RETIRED_STATUSES = {"deferred", "removed"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def emit(self, quiet: bool) -> int:
        if self.errors:
            print(f"FAIL — {len(self.errors)} error(s)")
            for item in self.errors:
                print(f"  ERROR  {item}")
        if self.warnings and not quiet:
            for item in self.warnings:
                print(f"  warn   {item}")
        if not self.errors:
            suffix = f" ({len(self.warnings)} warning(s))" if self.warnings else ""
            if not quiet or self.warnings:
                print(f"OK — plan integrity verified{suffix}")
        return 1 if self.errors else 0


# --------------------------------------------------------------------------
# Plan checks
# --------------------------------------------------------------------------

def check_plan(plan: Plan, report: Report) -> None:
    root = plan.root

    for problem in plan.problems:
        report.error(problem)

    for pf in plan.all_leaves():
        rel = pf.path.relative_to(root)
        for message in pf.errors:
            report.error(f"{rel}: {message}")
        if pf.id and not valid_id(pf.id):
            report.error(f"{rel}: malformed id '{pf.id}'")
        if pf.path.stem != pf.id:
            report.warn(f"{rel}: filename does not match id '{pf.id}'")

    known = plan.known_ids()

    # --- stories ---------------------------------------------------------
    for story in plan.stories.values():
        rel = story.path.relative_to(root)
        phase = story.get_str("phase")
        if phase and phase not in plan.phases:
            report.error(f"{rel}: phase '{phase}' does not exist")
        for req in story.get_list("requirements"):
            if req not in plan.requirements:
                report.error(f"{rel}: requirement '{req}' does not exist")
        for q in story.get_list("questions"):
            if q not in plan.questions:
                report.error(f"{rel}: question '{q}' does not exist")

    # --- endpoints -------------------------------------------------------
    for ep in plan.endpoints.values():
        rel = ep.path.relative_to(root)

        story_id = ep.get_str("story")
        if not story_id:
            report.error(f"{rel}: no story")
        elif story_id not in plan.stories:
            report.error(f"{rel}: story '{story_id}' does not exist")
        else:
            parent = plan.stories[story_id]
            if not parent.get_str("phase"):
                report.error(f"{rel}: story {story_id} has no phase")

        status = ep.get_str("status")
        if status not in ENDPOINT_STATUSES:
            report.error(f"{rel}: unknown status '{status}'")

        for req in ep.get_list("requirements"):
            if req not in plan.requirements:
                report.error(f"{rel}: requirement '{req}' does not exist")
        for err in ep.get_list("errors"):
            if err not in plan.errors:
                report.error(f"{rel}: error code '{err}' does not exist")
        for dec in ep.get_list("decisions"):
            if dec not in plan.decisions:
                report.error(f"{rel}: decision '{dec}' does not exist")

        open_questions = []
        for q in ep.get_list("questions"):
            if q not in plan.questions:
                report.error(f"{rel}: question '{q}' does not exist")
            elif plan.questions[q] == "open":
                open_questions.append(q)

        if status == "done" and open_questions:
            report.error(
                f"{rel}: marked done with open question(s) "
                f"{', '.join(open_questions)}"
            )

        contract = ep.get_str("contract")
        if contract and not (root / contract).is_file():
            if status in ("contracted", "tests-written", "building", "done"):
                report.error(f"{rel}: contract not found at {contract}")
            else:
                report.warn(f"{rel}: contract not yet written ({contract})")

    # --- change requests -------------------------------------------------
    for cr in plan.changes.values():
        rel = cr.path.relative_to(root)
        req = cr.get_str("requirement")
        if req and req not in plan.requirements:
            report.error(f"{rel}: requirement '{req}' does not exist")
        for us in cr.get_list("stories"):
            if us not in plan.stories:
                report.error(f"{rel}: story '{us}' does not exist")
        for ep_id in cr.get_list("endpoints"):
            if ep_id not in plan.endpoints:
                report.error(f"{rel}: endpoint '{ep_id}' does not exist")
        classification = cr.get_str("classification")
        if classification and classification not in ("additive", "breaking"):
            report.error(
                f"{rel}: classification must be additive or breaking, "
                f"got '{classification}'"
            )

    # --- requirement coverage -------------------------------------------
    claimed: set[str] = set()
    for story in plan.stories.values():
        claimed.update(story.get_list("requirements"))
    for ep in plan.endpoints.values():
        claimed.update(ep.get_list("requirements"))

    for req_id, status in sorted(plan.requirements.items()):
        if status in RETIRED_STATUSES:
            continue
        if req_id not in claimed:
            report.error(
                f"{req_id} is active but claimed by no story — "
                "assign it or mark it deferred"
            )

    # --- duplicate IDs across types --------------------------------------
    seen: dict[str, str] = {}
    for pf in plan.all_leaves():
        if pf.id in seen:
            report.error(f"id {pf.id} used by both {seen[pf.id]} and {pf.path.name}")
        seen[pf.id] = pf.path.name

    # --- loose references in prose ---------------------------------------
    for pf in plan.all_leaves():
        rel = pf.path.relative_to(root)
        body = pf.body.split("---", 2)[-1]
        for match in re.finditer(r"\b(REQ|PH|US|EP|DEC|Q|CR|ERR)-\d+\b", body):
            ref = match.group(0)
            if ref.endswith("-000") or ref.endswith("-0"):
                continue  # template placeholder
            if ref not in known:
                report.warn(f"{rel}: prose mentions unknown {ref}")


# --------------------------------------------------------------------------
# Toolkit cross-reference checks
# --------------------------------------------------------------------------

def check_toolkit(root: Path, report: Report) -> None:
    toolkit = root / ".claude"
    if not toolkit.is_dir():
        report.warn("no .claude/ directory — skipping toolkit checks")
        return

    referenced: set[str] = set()

    for path in toolkit.rglob("*.md"):
        if ".git" in path.parts or "project-template" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(root)
        for match in TOOLKIT_PATH.finditer(text):
            target = match.group(1)
            referenced.add(target)
            if not (toolkit / target).exists():
                report.error(f"{rel}: references missing .claude/{target}")

    for script in sorted((toolkit / "scripts").glob("*.py")):
        if script.name.startswith("_"):
            continue
        name = f"scripts/{script.name}"
        if name not in referenced:
            report.warn(f"{name} is never referenced by any skill, command, or hook")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit-only", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--quiet", action="store_true", help="suppress warnings")
    args = parser.parse_args()

    root = find_project_root()
    report = Report()

    if not args.toolkit_only:
        check_plan(load_plan(root), report)
    if not args.plan_only:
        check_toolkit(root, report)

    return report.emit(args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
