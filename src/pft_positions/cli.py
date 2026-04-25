"""Command line interface for the PFT position snapshot reference package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .canonical import canonical_json
from .fixtures import fixture_names, load_fixture
from .io import dump_json, load_json
from .validate import ValidationIssue, validate_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pft-positions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate a snapshot file or fixture directory")
    validate_parser.add_argument("path")

    parse_parser = subparsers.add_parser("parse", help="parse, validate, and print canonical JSON")
    parse_parser.add_argument("path")

    emit_parser = subparsers.add_parser("emit", help="emit a bundled fixture")
    emit_parser.add_argument("name", nargs="?", help="fixture name")
    emit_parser.add_argument("--list", action="store_true", help="list bundled fixture names")

    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate(args.path)
    if args.command == "parse":
        return _parse(args.path)
    if args.command == "emit":
        return _emit(args.name, args.list)
    return 2


def _validate(path: str) -> int:
    target = Path(path)
    if target.is_file():
        report = _file_report(target)
    else:
        files = [_file_report(file_path) for file_path in sorted(target.glob("*.json"))]
        report = {
            "valid": all(file_report["valid"] for file_report in files),
            "schema_version": None,
            "errors": [],
            "warnings": [],
            "files": files,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


def _parse(path: str) -> int:
    snapshot = load_json(path)
    issues = validate_snapshot(snapshot)
    if issues:
        print(f"FAIL {path}", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    print(canonical_json(snapshot))
    return 0


def _emit(name: str | None, list_requested: bool) -> int:
    if list_requested:
        for fixture_name in fixture_names():
            print(fixture_name)
        return 0
    if not name:
        print("fixture name required; use --list to see choices", file=sys.stderr)
        return 2
    try:
        fixture = load_fixture(name)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    dump_json(fixture, sys.stdout)
    return 0


def _file_report(path: Path) -> dict[str, object]:
    try:
        snapshot = load_json(path)
    except json.JSONDecodeError as exc:
        return _report_for_issues(path, None, [ValidationIssue("/", f"invalid JSON: {exc.msg}")])
    schema_version = snapshot.get("schema_version") if isinstance(snapshot, dict) else None
    if not isinstance(snapshot, dict):
        return _report_for_issues(path, schema_version, [ValidationIssue("/", "snapshot must be a JSON object")])
    return _report_for_issues(path, schema_version, validate_snapshot(snapshot))


def _report_for_issues(
    path: Path,
    schema_version: object,
    issues: list[ValidationIssue],
) -> dict[str, object]:
    return {
        "valid": not issues,
        "schema_version": schema_version,
        "errors": [
            {
                "path": issue.path,
                "message": issue.message,
            }
            for issue in issues
        ],
        "warnings": [],
        "file": str(path),
    }


if __name__ == "__main__":
    raise SystemExit(main())
