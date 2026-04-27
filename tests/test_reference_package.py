from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pft_positions.canonical import canonical_json, content_hash
from pft_positions.fixtures import fixture_names, load_fixture
from pft_positions.validate import validate_file, validate_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


@pytest.mark.parametrize("fixture_path", sorted(FIXTURES.glob("*.json")))
def test_authoritative_fixtures_validate(fixture_path: Path) -> None:
    assert validate_file(fixture_path) == []


@pytest.mark.parametrize("fixture_path", sorted(FIXTURES.glob("*.json")))
def test_fixture_hashes_match_deterministic_hash(fixture_path: Path) -> None:
    snapshot = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert snapshot["provenance"]["content_hash"] == content_hash(snapshot)


def test_hash_is_stable_across_key_order_and_whitespace() -> None:
    snapshot = load_fixture("delta-one")
    reordered = _reverse_object_keys(snapshot)
    pretty_roundtrip = json.loads(json.dumps(reordered, indent=4))
    assert content_hash(snapshot) == content_hash(pretty_roundtrip)


def test_canonical_json_is_stable() -> None:
    snapshot = load_fixture("delta-one")
    assert canonical_json(snapshot) == canonical_json(json.loads(canonical_json(snapshot)))


def test_semantic_mutation_changes_hash() -> None:
    snapshot = load_fixture("delta-one")
    mutated = json.loads(json.dumps(snapshot))
    mutated["positions"][0]["quantity"] = "2.00"
    assert content_hash(snapshot) != content_hash(mutated)


def test_missing_required_schema_field_fails_validation() -> None:
    snapshot = load_fixture("delta-one")
    del snapshot["positions"][0]["risk"]["value_at_risk_1d"]
    assert any(issue.path == "/positions/0/risk/value_at_risk_1d" for issue in validate_snapshot(snapshot))


def test_hash_mismatch_fails_validation() -> None:
    snapshot = load_fixture("delta-one")
    snapshot["provenance"]["content_hash"] = "0" * 64
    assert any(issue.path == "/provenance/content_hash" for issue in validate_snapshot(snapshot))


def test_fixture_names_are_declared() -> None:
    assert fixture_names() == ["delta-one", "hyperliquid-hlp-child", "option", "yield"]


def test_raw_fixtures_are_paired_with_normalized_fixtures() -> None:
    raw_dir = FIXTURES / "raw"
    expected = {
        "delta-one.raw.json": "../delta-one.json",
        "hyperliquid-hlp-child.raw.json": "../hyperliquid-hlp-child.json",
        "option.raw.json": "../option.json",
        "yield.raw.json": "../yield.json",
    }
    for raw_name, normalized_ref in expected.items():
        raw = json.loads((raw_dir / raw_name).read_text(encoding="utf-8"))
        assert raw["normalizes_to"] == normalized_ref
        assert (raw_dir / normalized_ref).resolve().is_file()


def test_validate_cli_accepts_fixture_directory() -> None:
    result = _run_cli("validate", str(FIXTURES))
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["valid"] is True
    assert report["schema_version"] is None
    assert report["errors"] == []
    assert report["warnings"] == []
    assert [Path(file_report["file"]).name for file_report in report["files"]] == [
        "delta-one.json",
        "hyperliquid-hlp-child.json",
        "option.json",
        "yield.json",
    ]
    assert all(file_report["schema_version"] == "position-snapshot.v0" for file_report in report["files"])


def test_validate_cli_rejects_bad_file(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    snapshot = load_fixture("delta-one")
    snapshot["provenance"]["content_hash"] = "0" * 64
    bad_file.write_text(json.dumps(snapshot), encoding="utf-8")
    result = _run_cli("validate", str(bad_file))
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["valid"] is False
    assert report["schema_version"] == "position-snapshot.v0"
    assert report["warnings"] == []
    assert any(error["path"] == "/provenance/content_hash" for error in report["errors"])


def test_validate_cli_file_report_has_required_fields() -> None:
    result = _run_cli("validate", str(FIXTURES / "delta-one.json"))
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert set(["valid", "schema_version", "errors", "warnings"]).issubset(report)
    assert report["valid"] is True
    assert report["schema_version"] == "position-snapshot.v0"
    assert report["errors"] == []
    assert report["warnings"] == []


def test_emit_cli_outputs_valid_fixture_json() -> None:
    result = _run_cli("emit", "delta-one")
    assert result.returncode == 0
    snapshot = json.loads(result.stdout)
    assert validate_snapshot(snapshot) == []


def test_hyperliquid_fixture_contains_full_hlp_child_snapshot() -> None:
    snapshot = load_fixture("hyperliquid-hlp-child")
    positions = snapshot["positions"]
    assert len(positions) == 190
    assert {position["instrument_type"] for position in positions} == {"linear"}
    assert all(position["venue"]["venue_id"] == "hyperliquid" for position in positions)
    assert all(position["account_ref"].startswith("hyperliquid:0x010461") for position in positions)
    assert any(position["linear"]["symbol"] == "BTC-PERP" for position in positions)


def test_parse_cli_outputs_canonical_json() -> None:
    result = _run_cli("parse", str(FIXTURES / "delta-one.json"))
    assert result.returncode == 0
    assert result.stdout.rstrip("\n") == canonical_json(load_fixture("delta-one"))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "pft_positions.cli", *args],
        check=False,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def _reverse_object_keys(value):
    if isinstance(value, dict):
        return {key: _reverse_object_keys(value[key]) for key in reversed(list(value.keys()))}
    if isinstance(value, list):
        return [_reverse_object_keys(item) for item in value]
    return value
