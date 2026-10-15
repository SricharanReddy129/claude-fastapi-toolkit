#!/usr/bin/env python3
"""
dal_guard.py — static checks for the invariants that leak data when broken.

Called by:  hook .claude/hooks/on_dal_edit.py
            .claude/commands/verify-story.md
            .claude/commands/security-review.md
Calls:      nothing (stdlib ast only)

Stdlib only.

Checks the rules from .claude/skills/dal-conventions.md and
.claude/skills/service-conventions.md that are mechanically detectable:

  - every DAL query filters on tenant
  - every DAL query filters out soft-deleted rows
  - tenant is never read from request input
  - services never create or commit a session
  - os.getenv appears only in app/settings.py
  - no blocking calls inside async functions

This is a lint, not a proof. It reads the AST and reasons about names, so
it will miss cleverly indirect code and will occasionally flag something
fine. A finding is a prompt to look, not a verdict.

The security-reviewer subagent covers what this cannot.

Exit code 0 when clean, 1 when any error is found.

Usage:
    python .claude/scripts/dal_guard.py
    python .claude/scripts/dal_guard.py app/dal/invoices.py
    python .claude/scripts/dal_guard.py --quiet
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------

TENANT_NAMES = {"tenant_id", "tenantid", "tenant"}
DELETED_NAMES = {
    "deleted_at", "is_deleted", "deleted", "removed_at", "archived_at",
}

# Calls that read a query. A function containing one of these is doing data
# access and must carry the mandatory filters.
QUERY_CALLS = {"select", "query", "update", "delete", "exists"}
FILTER_CALLS = {"filter", "filter_by", "where", "having"}

# Names that mean a request-controlled value reached this scope.
REQUEST_SOURCES = {
    "Body", "Query", "Path", "Header", "Cookie", "Form", "File",
    "request", "payload", "body",
}

# Blocking calls that must not appear inside an async function.
BLOCKING_CALLS = {
    "requests.get", "requests.post", "requests.put", "requests.delete",
    "requests.patch", "requests.head", "requests.request",
    "urlopen", "urlretrieve",
    "time.sleep",
    "subprocess.run", "subprocess.call", "subprocess.check_output",
}
BLOCKING_BARE = {"open", "input"}

COMMIT_NAMES = {"commit", "flush"}
SESSION_FACTORIES = {
    "sessionmaker", "async_sessionmaker", "Session", "AsyncSession",
    "create_engine", "create_async_engine",
}


@dataclass
class Finding:
    path: str
    line: int
    severity: str          # error | warn
    rule: str
    message: str
    skill: str


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def dotted_name(node: ast.AST) -> str:
    """Best-effort dotted name for a call target."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def names_in(node: ast.AST) -> set[str]:
    """Every identifier, attribute, and string literal under a node."""
    found: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            found.add(sub.id.lower())
        elif isinstance(sub, ast.Attribute):
            found.add(sub.attr.lower())
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            found.add(sub.value.lower())
        elif isinstance(sub, ast.keyword) and sub.arg:
            found.add(sub.arg.lower())
    return found


def calls_in(node: ast.AST) -> set[str]:
    out: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            name = dotted_name(sub.func)
            if name:
                out.add(name)
                out.add(name.rsplit(".", 1)[-1])
    return out


def is_query_function(func: ast.AST) -> bool:
    return bool(calls_in(func) & QUERY_CALLS)


def has_filter_on(func: ast.AST, candidates: set[str]) -> bool:
    """True if any filter-ish call or comparison mentions one of the names."""
    for sub in ast.walk(func):
        if isinstance(sub, ast.Call):
            name = dotted_name(sub.func).rsplit(".", 1)[-1]
            if name in FILTER_CALLS and names_in(sub) & candidates:
                return True
        elif isinstance(sub, ast.Compare) and names_in(sub) & candidates:
            return True
    return False


def param_names(func: ast.AST) -> set[str]:
    if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return set()
    args = func.args
    everything = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    if args.vararg:
        everything.append(args.vararg)
    if args.kwarg:
        everything.append(args.kwarg)
    return {a.arg.lower() for a in everything}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_dal(path: Path, rel: str, tree: ast.AST) -> list[Finding]:
    out: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        if not is_query_function(node):
            continue

        if node.name.lower().startswith("cross_tenant") or "cross_tenant" in (
            ast.get_docstring(node) or ""
        ).lower():
            out.append(
                Finding(
                    rel, node.lineno, "warn", "cross-tenant",
                    f"{node.name}() is declared cross-tenant — "
                    "confirm it is recorded in plan/decisions.md",
                    "dal-conventions",
                )
            )
            continue

        if not has_filter_on(node, TENANT_NAMES) and not (
            param_names(node) & TENANT_NAMES
        ):
            out.append(
                Finding(
                    rel, node.lineno, "error", "tenant-filter",
                    f"{node.name}() queries without filtering on tenant",
                    "dal-conventions",
                )
            )

        if not has_filter_on(node, DELETED_NAMES):
            out.append(
                Finding(
                    rel, node.lineno, "warn", "soft-delete-filter",
                    f"{node.name}() has no soft-delete filter — "
                    "confirm the table does not soft-delete",
                    "dal-conventions",
                )
            )

        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                if dotted_name(sub.func).rsplit(".", 1)[-1] in COMMIT_NAMES:
                    out.append(
                        Finding(
                            rel, sub.lineno, "error", "dal-commit",
                            "DAL must not commit — the caller owns the transaction",
                            "dal-conventions",
                        )
                    )
    return out


def check_tenant_source(rel: str, tree: ast.AST) -> list[Finding]:
    """Flag a tenant value that appears to arrive from request input."""
    out: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
            if arg.arg.lower() not in TENANT_NAMES:
                continue
            annotation = ast.unparse(arg.annotation) if arg.annotation else ""
            if any(src in annotation for src in REQUEST_SOURCES):
                out.append(
                    Finding(
                        rel, arg.lineno, "error", "tenant-from-input",
                        f"{node.name}() takes tenant from request input — "
                        "it must come from the validated token context",
                        "dal-conventions",
                    )
                )
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            target = dotted_name(node.value).lower()
            if any(src.lower() in target for src in ("request", "payload", "body")):
                key = ""
                if isinstance(node.slice, ast.Constant) and isinstance(
                    node.slice.value, str
                ):
                    key = node.slice.value.lower()
                if key in TENANT_NAMES:
                    out.append(
                        Finding(
                            rel, node.lineno, "error", "tenant-from-input",
                            "tenant read from request data",
                            "dal-conventions",
                        )
                    )
    return out


def check_service(rel: str, tree: ast.AST) -> list[Finding]:
    out: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            tail = name.rsplit(".", 1)[-1]
            if tail in COMMIT_NAMES:
                out.append(
                    Finding(
                        rel, node.lineno, "error", "service-commit",
                        "services must not commit — they accept an injected session",
                        "service-conventions",
                    )
                )
            if tail in SESSION_FACTORIES:
                out.append(
                    Finding(
                        rel, node.lineno, "error", "service-session",
                        f"services must not create a session ({tail})",
                        "service-conventions",
                    )
                )
            if name in ("HTTPException",) or tail == "HTTPException":
                out.append(
                    Finding(
                        rel, node.lineno, "error", "service-http",
                        "services raise registry errors, never HTTPException",
                        "service-conventions",
                    )
                )
    return out


def check_getenv(rel: str, tree: ast.AST) -> list[Finding]:
    out: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name in ("os.getenv", "os.environ.get") or name.endswith(
                "environ.get"
            ):
                out.append(
                    Finding(
                        rel, node.lineno, "error", "getenv",
                        "read configuration from app/settings.py, not os.getenv",
                        "service-conventions",
                    )
                )
    return out


def check_blocking_async(rel: str, tree: ast.AST) -> list[Finding]:
    out: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            name = dotted_name(sub.func)
            tail = name.rsplit(".", 1)[-1]
            if name in BLOCKING_CALLS or (
                tail in BLOCKING_BARE and not isinstance(sub.func, ast.Attribute)
            ):
                out.append(
                    Finding(
                        rel, sub.lineno, "error", "blocking-async",
                        f"{name or tail}() blocks the event loop for every "
                        "concurrent request — offload it to a thread",
                        "dal-conventions",
                    )
                )
    return out


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def analyse(root: Path, path: Path) -> list[Finding]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        return [Finding(rel, 0, "warn", "parse", f"could not parse: {exc}", "—")]

    findings: list[Finding] = []
    in_dal = "/dal/" in f"/{rel}"
    in_service = "/services/" in f"/{rel}"
    is_settings = rel.endswith("app/settings.py") or rel.endswith("settings.py")

    if in_dal:
        findings += check_dal(path, rel, tree)
    if in_service:
        findings += check_service(rel, tree)
    if not is_settings:
        findings += check_getenv(rel, tree)

    findings += check_tenant_source(rel, tree)
    findings += check_blocking_async(rel, tree)
    return findings


def targets(root: Path, given: list[str]) -> list[Path]:
    if given:
        out: list[Path] = []
        for item in given:
            path = Path(item)
            if not path.is_absolute():
                path = root / path
            if path.is_dir():
                out.extend(sorted(path.rglob("*.py")))
            elif path.is_file():
                out.append(path)
        return out

    app = root / "app"
    return sorted(app.rglob("*.py")) if app.is_dir() else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="files or directories")
    parser.add_argument("--quiet", action="store_true", help="suppress warnings")
    args = parser.parse_args()

    here = Path(__file__).resolve()
    root = next(
        (p.parent for p in [here, *here.parents] if p.name == ".claude"),
        Path.cwd(),
    )

    files = targets(root, args.paths)
    if not files:
        print("No Python files to check (is app/ created yet?)")
        return 0

    findings: list[Finding] = []
    for path in files:
        findings.extend(analyse(root, path))

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warn"]

    if errors:
        print(f"FAIL — {len(errors)} error(s)")
        for f in errors:
            print(f"  {f.path}:{f.line}  [{f.rule}]  {f.message}")
            print(f"      see .claude/skills/{f.skill}.md")

    if warnings and not args.quiet:
        if errors:
            print()
        for f in warnings:
            print(f"  warn  {f.path}:{f.line}  [{f.rule}]  {f.message}")

    if not errors:
        suffix = f" ({len(warnings)} warning(s))" if warnings else ""
        print(f"OK — {len(files)} file(s) checked{suffix}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
