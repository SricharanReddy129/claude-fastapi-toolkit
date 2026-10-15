#!/usr/bin/env python3
"""
trace_impact.py — trace a requirement forward to everything it touches.

Called by:  .claude/commands/change-request.md
            .claude/commands/new-requirement.md (contradiction check)
Calls:      .claude/scripts/_plan.py

Stdlib only.

Answers the question /change-request must answer before anything is edited:
if this requirement changes, what else has to change?

The chain runs requirement -> stories -> endpoints -> contracts -> tests.
It is only traceable because plan files declare their parents — see
.claude/skills/plan-file-format.md.

Endpoints already marked `done` are flagged separately. Those are the
expensive ones: work that must be redone rather than merely re-planned.

Usage:
    python .claude/scripts/trace_impact.py REQ-014
    python .claude/scripts/trace_impact.py REQ-014 --format md
    python .claude/scripts/trace_impact.py --orphans
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _plan import (  # noqa: E402
    Plan,
    PlanFile,
    find_project_root,
    load_plan,
    valid_id,
)

DONE = "done"
EXPENSIVE = {"done", "building", "tests-written"}

# Test files are found by convention rather than declared, since a plan file
# does not record its tests. Reported as candidates, not as fact.
TEST_DIRS = ("tests",)


def collect(plan: Plan, req_id: str) -> dict[str, object]:
    stories = [
        s for s in plan.stories.values() if req_id in s.get_list("requirements")
    ]
    story_ids = {s.id for s in stories}

    endpoints: list[PlanFile] = []
    for ep in plan.endpoints.values():
        direct = req_id in ep.get_list("requirements")
        via_story = ep.get_str("story") in story_ids
        if direct or via_story:
            endpoints.append(ep)

    endpoints.sort(key=lambda e: e.id)
    stories.sort(key=lambda s: s.id)

    contracts = []
    for ep in endpoints:
        path = ep.get_str("contract")
        if path:
            contracts.append((ep.id, path, (plan.root / path).is_file()))

    errors: set[str] = set()
    questions: set[str] = set()
    decisions: set[str] = set()
    for item in [*stories, *endpoints]:
        errors.update(item.get_list("errors"))
        questions.update(item.get_list("questions"))
        decisions.update(item.get_list("decisions"))

    changes = [
        cr for cr in plan.changes.values() if cr.get_str("requirement") == req_id
    ]
    changes.sort(key=lambda c: c.id)

    tests = find_tests(plan.root, endpoints)

    return {
        "stories": stories,
        "endpoints": endpoints,
        "contracts": contracts,
        "errors": sorted(errors),
        "questions": sorted(questions),
        "decisions": sorted(decisions),
        "changes": changes,
        "tests": tests,
    }


def find_tests(root: Path, endpoints: list[PlanFile]) -> dict[str, list[str]]:
    """Find test files that mention each endpoint's ID or path.

    Convention-based, so treat the result as candidates to review rather
    than a complete list.
    """
    found: dict[str, list[str]] = {ep.id: [] for ep in endpoints}
    if not endpoints:
        return found

    candidates: list[Path] = []
    for dirname in TEST_DIRS:
        folder = root / dirname
        if folder.is_dir():
            candidates.extend(sorted(folder.rglob("*.py")))

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(path.relative_to(root))
        for ep in endpoints:
            ep_path = ep.get_str("path")
            if ep.id in text or (ep_path and ep_path in text):
                found[ep.id].append(rel)
    return found


def report_text(plan: Plan, req_id: str, data: dict[str, object]) -> list[str]:
    out: list[str] = []
    status = plan.requirements.get(req_id, "**NOT IN INVENTORY**")
    out.append(f"Impact of {req_id}  (status: {status})")
    out.append("=" * 60)

    stories: list[PlanFile] = data["stories"]          # type: ignore[assignment]
    endpoints: list[PlanFile] = data["endpoints"]      # type: ignore[assignment]

    if not stories and not endpoints:
        out.append("")
        out.append("Nothing claims this requirement.")
        out.append("Either it is new, or it was never assigned to a story.")
        return out

    out.append("")
    out.append(f"Stories ({len(stories)})")
    for s in stories:
        out.append(f"  {s.id:<10} {s.get_str('status'):<13} {s.get_str('name')}")

    out.append("")
    out.append(f"Endpoints ({len(endpoints)})")
    for ep in endpoints:
        via = "" if req_id in ep.get_list("requirements") else "  (via story)"
        out.append(
            f"  {ep.id:<10} {ep.get_str('status'):<15} "
            f"{ep.get_str('method'):<7} {ep.get_str('path')}{via}"
        )

    expensive = [e for e in endpoints if e.get_str("status") in EXPENSIVE]
    if expensive:
        out.append("")
        out.append(f"!! Already built or in progress ({len(expensive)})")
        out.append("   These must be redone, not merely re-planned.")
        for ep in expensive:
            out.append(f"     {ep.id}  [{ep.get_str('status')}]")

    contracts = data["contracts"]
    if contracts:
        out.append("")
        out.append(f"Contracts ({len(contracts)})")
        for ep_id, path, exists in contracts:  # type: ignore[misc]
            flag = "" if exists else "   MISSING"
            out.append(f"  {ep_id:<10} {path}{flag}")

    tests: dict[str, list[str]] = data["tests"]        # type: ignore[assignment]
    hits = {k: v for k, v in tests.items() if v}
    if hits:
        out.append("")
        out.append("Test files (found by convention — review, do not trust)")
        for ep_id, paths in sorted(hits.items()):
            for path in paths:
                out.append(f"  {ep_id:<10} {path}")

    for label, key in (("Error codes", "errors"), ("Decisions", "decisions")):
        values = data[key]
        if values:
            out.append("")
            out.append(f"{label}: {', '.join(values)}")  # type: ignore[arg-type]

    questions: list[str] = data["questions"]           # type: ignore[assignment]
    if questions:
        open_q = [q for q in questions if plan.questions.get(q) == "open"]
        out.append("")
        out.append(f"Questions: {', '.join(questions)}")
        if open_q:
            out.append(f"  OPEN: {', '.join(open_q)} — resolve before proceeding")

    changes: list[PlanFile] = data["changes"]          # type: ignore[assignment]
    if changes:
        out.append("")
        out.append("Previous change requests")
        for cr in changes:
            out.append(
                f"  {cr.id:<10} {cr.get_str('date'):<12} "
                f"{cr.get_str('classification'):<10} {cr.get_str('status')}"
            )

    out.append("")
    out.append("-" * 60)
    out.append("Next: classify each contract change additive or breaking,")
    out.append("then stop for approval. See .claude/skills/contract-authoring.md")
    return out


def report_markdown(plan: Plan, req_id: str, data: dict[str, object]) -> list[str]:
    stories: list[PlanFile] = data["stories"]          # type: ignore[assignment]
    endpoints: list[PlanFile] = data["endpoints"]      # type: ignore[assignment]
    status = plan.requirements.get(req_id, "**NOT IN INVENTORY**")

    out = [f"## Impact — {req_id}", "", f"**Requirement status:** {status}", ""]

    if not stories and not endpoints:
        out.append("Nothing claims this requirement.")
        return out

    out += ["| Affected | IDs |", "|---|---|"]
    out.append(f"| Stories | {', '.join(s.id for s in stories) or '—'} |")
    out.append(f"| Endpoints | {', '.join(e.id for e in endpoints) or '—'} |")
    contracts = data["contracts"]
    out.append(
        f"| Contracts | {', '.join(p for _, p, _ in contracts) or '—'} |"  # type: ignore[misc]
    )
    out.append(f"| Error codes | {', '.join(data['errors']) or '—'} |")  # type: ignore[arg-type]
    out.append("")

    out += ["| Endpoint | Method | Path | Status |", "|---|---|---|---|"]
    for ep in endpoints:
        out.append(
            f"| {ep.id} | {ep.get_str('method')} | `{ep.get_str('path')}` "
            f"| {ep.get_str('status')} |"
        )

    expensive = [e for e in endpoints if e.get_str("status") in EXPENSIVE]
    if expensive:
        out += [
            "",
            f"**Already built or in progress:** {', '.join(e.id for e in expensive)}",
            "",
            "These must be redone, not merely re-planned.",
        ]
    return out


def report_orphans(plan: Plan) -> int:
    claimed: set[str] = set()
    for item in [*plan.stories.values(), *plan.endpoints.values()]:
        claimed.update(item.get_list("requirements"))

    orphans = [
        (r, s)
        for r, s in sorted(plan.requirements.items())
        if s not in ("deferred", "removed") and r not in claimed
    ]

    if not orphans:
        print("OK — every active requirement is claimed by a story")
        return 0

    print(f"{len(orphans)} active requirement(s) claimed by nothing:\n")
    for req, status in orphans:
        print(f"  {req:<10} {status}")
    print("\nAssign each to a story, or mark it deferred with a reason.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirement", nargs="?", help="e.g. REQ-014")
    parser.add_argument("--format", choices=("text", "md"), default="text")
    parser.add_argument(
        "--orphans",
        action="store_true",
        help="list active requirements claimed by no story",
    )
    args = parser.parse_args()

    root = find_project_root()
    plan = load_plan(root)

    if plan.problems:
        print(f"WARNING — {len(plan.problems)} plan file(s) unreadable:")
        for problem in plan.problems:
            print(f"  {problem}")
        print("Trace may be incomplete.\n")

    if args.orphans:
        return report_orphans(plan)

    if not args.requirement:
        parser.error("give a requirement ID, or use --orphans")

    req_id = args.requirement.upper()
    if not valid_id(req_id) or not req_id.startswith("REQ-"):
        parser.error(f"'{args.requirement}' is not a requirement ID")

    if req_id not in plan.requirements:
        print(f"WARNING: {req_id} is not in plan/requirements/inventory.md")
        print("Tracing references anyway.\n")

    data = collect(plan, req_id)
    lines = (
        report_markdown(plan, req_id, data)
        if args.format == "md"
        else report_text(plan, req_id, data)
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
