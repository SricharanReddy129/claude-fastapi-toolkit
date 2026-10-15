#!/usr/bin/env python3
"""
contract_diff.py — compare the live OpenAPI output against committed contracts.

Called by:  .claude/commands/build-endpoint.md
            .claude/commands/verify-story.md
Calls:      .claude/scripts/_plan.py

Runs inside the project's Poetry environment, because it imports the app:

    poetry run python .claude/scripts/contract_diff.py

NOT callable from a hook — hooks run outside the Poetry environment. Use
--from-file to diff a previously exported spec when importing is not possible.

The contract is the source of truth. If code and contract disagree, that is
a bug — see .claude/skills/contract-authoring.md. Without this check,
contracts rot within a month and become documentation nobody trusts.

What is compared: the machine-readable frontmatter — path, method, success
status, error statuses. Field-level shapes are verified by the contract
tests instead, because parsing prose tables would be unreliable and a check
that pretends to verify more than it can is worse than one that is honest.

Exit code 0 when contracts and app agree, 1 on any drift.

Usage:
    poetry run python .claude/scripts/contract_diff.py
    poetry run python .claude/scripts/contract_diff.py --app app.main:app
    poetry run python .claude/scripts/contract_diff.py --export openapi.json
    python .claude/scripts/contract_diff.py --from-file openapi.json
    poetry run python .claude/scripts/contract_diff.py --story US-003
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _plan import (  # noqa: E402
    find_project_root,
    load_plan,
    parse_frontmatter,
    FrontmatterError,
)

DEFAULT_APP = "app.main:app"
METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

# FastAPI path params are {name}; normalise so names do not cause false drift.
PARAM = re.compile(r"\{[^}]+\}")


def normalise(path: str) -> str:
    path = PARAM.sub("{}", path.strip())
    return path.rstrip("/") or "/"


# --------------------------------------------------------------------------
# Loading the live spec
# --------------------------------------------------------------------------

def load_spec_from_app(root: Path, target: str) -> dict:
    """Import the FastAPI app and return its OpenAPI document."""
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    module_name, _, attr = target.partition(":")
    attr = attr or "app"

    try:
        module = __import__(module_name, fromlist=["*"])
    except ImportError as exc:
        raise SystemExit(
            f"ERROR: could not import '{module_name}': {exc}\n\n"
            "This script imports the app, so it must run inside the project\n"
            "environment:\n"
            "    poetry run python .claude/scripts/contract_diff.py\n\n"
            "If the app cannot be imported, export the spec once and use\n"
            "--from-file instead."
        ) from exc

    app = getattr(module, attr, None)
    if app is None:
        raise SystemExit(f"ERROR: '{module_name}' has no attribute '{attr}'")

    openapi = getattr(app, "openapi", None)
    if not callable(openapi):
        raise SystemExit(f"ERROR: {target} does not look like a FastAPI app")

    return openapi()


def load_spec_from_file(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"ERROR: no such file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: {path} is not valid JSON: {exc}") from exc


def routes_from_spec(spec: dict) -> dict[tuple[str, str], dict]:
    """Return {(method, normalised_path): operation}."""
    out: dict[tuple[str, str], dict] = {}
    for raw_path, operations in (spec.get("paths") or {}).items():
        for method, operation in (operations or {}).items():
            if method.lower() in METHODS:
                out[(method.lower(), normalise(raw_path))] = operation or {}
    return out


# --------------------------------------------------------------------------
# Loading contracts
# --------------------------------------------------------------------------

def load_contracts(root: Path) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """Return {(method, normalised_path): contract} plus any parse problems."""
    contracts: dict[tuple[str, str], dict] = {}
    problems: list[str] = []

    folder = root / "contracts"
    if not folder.is_dir():
        return contracts, [f"no contracts/ directory at {folder}"]

    for path in sorted(folder.rglob("*.md")):
        if path.name == "_template.md":
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            data = parse_frontmatter(path.read_text(encoding="utf-8"))
        except FrontmatterError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        except OSError as exc:
            problems.append(f"{rel}: {exc}")
            continue

        method = str(data.get("method", "")).lower()
        route = str(data.get("path", ""))
        if not method or not route:
            problems.append(f"{rel}: frontmatter needs both method and path")
            continue
        if method not in METHODS:
            problems.append(f"{rel}: unknown method '{method}'")
            continue

        data["_file"] = rel
        key = (method, normalise(route))
        if key in contracts:
            problems.append(
                f"{rel}: duplicate contract for {method.upper()} {route} "
                f"(also {contracts[key]['_file']})"
            )
            continue
        contracts[key] = data

    return contracts, problems


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------

def statuses_of(operation: dict) -> set[int]:
    out: set[int] = set()
    for code in (operation.get("responses") or {}):
        try:
            out.add(int(code))
        except (TypeError, ValueError):
            continue
    return out


def compare(
    contracts: dict[tuple[str, str], dict],
    routes: dict[tuple[str, str], dict],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key, contract in sorted(contracts.items()):
        method, path = key
        label = f"{method.upper()} {path}"
        rel = contract.get("_file", "?")

        if key not in routes:
            errors.append(
                f"{rel}: contract declares {label} but the app has no such route"
            )
            continue

        operation = routes[key]
        live = statuses_of(operation)

        success = contract.get("status_success")
        if success:
            try:
                want = int(str(success))
            except ValueError:
                errors.append(f"{rel}: status_success '{success}' is not a number")
                want = 0
            if want and want not in live:
                errors.append(
                    f"{rel}: contract says success {want}, "
                    f"app returns {sorted(live) or 'nothing declared'}"
                )

        declared_errors = contract.get("status_errors") or []
        if isinstance(declared_errors, list):
            for code in declared_errors:
                try:
                    want = int(str(code))
                except ValueError:
                    errors.append(f"{rel}: status_errors contains '{code}'")
                    continue
                # 422 comes from Pydantic automatically; 401/403 often come
                # from middleware and may not appear per-route in the spec.
                if want not in live and want not in (401, 403, 422):
                    warnings.append(
                        f"{rel}: contract declares {want} but the app "
                        f"does not document it on {label}"
                    )

    for key in sorted(routes):
        method, path = key
        if path.startswith(("/docs", "/redoc", "/openapi")):
            continue
        if key not in contracts:
            errors.append(
                f"app serves {method.upper()} {path} with no committed contract"
            )

    return errors, warnings


def filter_to_story(
    root: Path, contracts: dict[tuple[str, str], dict], story_id: str
) -> dict[tuple[str, str], dict]:
    plan = load_plan(root)
    if story_id not in plan.stories:
        raise SystemExit(f"ERROR: no such story: {story_id}")

    wanted = {
        ep.id
        for ep in plan.endpoints.values()
        if ep.get_str("story") == story_id
    }
    if not wanted:
        raise SystemExit(f"ERROR: {story_id} has no endpoints")

    return {
        key: c
        for key, c in contracts.items()
        if str(c.get("endpoint", "")) in wanted
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", default=DEFAULT_APP, help=f"default {DEFAULT_APP}")
    parser.add_argument("--from-file", help="diff a previously exported openapi.json")
    parser.add_argument("--export", help="write the live spec to this path and exit")
    parser.add_argument("--story", help="check only one story's endpoints")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = find_project_root()

    spec = (
        load_spec_from_file(Path(args.from_file))
        if args.from_file
        else load_spec_from_app(root, args.app)
    )

    if args.export:
        target = Path(args.export)
        if not target.is_absolute():
            target = root / target
        target.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        print(f"Wrote {target}")
        return 0

    contracts, problems = load_contracts(root)
    if args.story:
        contracts = filter_to_story(root, contracts, args.story)

    routes = routes_from_spec(spec)
    errors, warnings = compare(contracts, routes)
    errors = problems + errors

    if errors:
        print(f"DRIFT — {len(errors)} problem(s)")
        for item in errors:
            print(f"  ERROR  {item}")
        print(
            "\nThe contract is the source of truth. Either fix the "
            "implementation,\nor raise a change request — never edit the "
            "contract to match the code."
        )

    if warnings and not args.quiet:
        if errors:
            print()
        for item in warnings:
            print(f"  warn   {item}")

    if not errors:
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        print(f"OK — {len(contracts)} contract(s) match the app{suffix}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
