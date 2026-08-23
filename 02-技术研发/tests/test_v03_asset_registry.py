from __future__ import annotations

import copy
import json
import runpy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = (
    ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
)
GENERATOR_PATH = PACKAGE / "99_验证与清单" / "generate_v03_contracts.py"
VALIDATOR_PATH = PACKAGE / "99_验证与清单" / "validate_v03_deliverables.py"
UNITY_PROJECT = ROOT / "02-技术研发" / "04-Unity视觉" / "SRP-Weather-Visual"


def authorities() -> tuple[dict[str, str], set[str]]:
    manifest = json.loads(
        (UNITY_PROJECT / "Packages" / "manifest.json").read_text(encoding="utf-8")
    )
    ledger = json.loads(
        (UNITY_PROJECT / "Governance" / "asset_license_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    return manifest["dependencies"], set(ledger["groups"])


def test_v03_asset_registry_accepts_generated_authority() -> None:
    registry = runpy.run_path(str(GENERATOR_PATH))["asset_registry"]()
    validate = runpy.run_path(str(VALIDATOR_PATH))["validate_asset_registry"]
    dependencies, ledger_groups = authorities()

    validate(registry, dependencies, ledger_groups)


def test_v03_asset_registry_rejects_missing_category() -> None:
    registry = runpy.run_path(str(GENERATOR_PATH))["asset_registry"]()
    registry = copy.deepcopy(registry)
    registry["entries"] = [
        entry for entry in registry["entries"] if entry["category"] != "FONT"
    ]
    registry["design_entry_count"] -= 1
    registry["entry_count"] -= 1
    validate = runpy.run_path(str(VALIDATOR_PATH))["validate_asset_registry"]
    dependencies, ledger_groups = authorities()

    with pytest.raises(AssertionError):
        validate(registry, dependencies, ledger_groups)


def test_v03_asset_registry_rejects_missing_required_field() -> None:
    registry = runpy.run_path(str(GENERATOR_PATH))["asset_registry"]()
    registry = copy.deepcopy(registry)
    registry["entries"][0].pop("owner")
    validate = runpy.run_path(str(VALIDATOR_PATH))["validate_asset_registry"]
    dependencies, ledger_groups = authorities()

    with pytest.raises(AssertionError, match="asset fields drifted"):
        validate(registry, dependencies, ledger_groups)


def test_v03_asset_registry_rejects_manifest_drift() -> None:
    registry = runpy.run_path(str(GENERATOR_PATH))["asset_registry"]()
    validate = runpy.run_path(str(VALIDATOR_PATH))["validate_asset_registry"]
    dependencies, ledger_groups = authorities()
    dependencies = dict(dependencies)
    dependencies["example.unclassified.package"] = "1.0.0"

    with pytest.raises(AssertionError):
        validate(registry, dependencies, ledger_groups)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("extra_field", "asset fields drifted"),
        ("duplicate_id", "duplicate V-03 asset_id"),
        ("unknown_ledger_group", "unknown ledger group"),
        ("premature_formal_use", "asset prematurely allowed"),
    ),
)
def test_v03_asset_registry_rejects_fail_closed_mutations(
    mutation: str, message: str
) -> None:
    registry = runpy.run_path(str(GENERATOR_PATH))["asset_registry"]()
    registry = copy.deepcopy(registry)
    if mutation == "extra_field":
        registry["entries"][0]["unexpected"] = "must be rejected"
    elif mutation == "duplicate_id":
        registry["entries"][1]["asset_id"] = registry["entries"][0]["asset_id"]
    elif mutation == "unknown_ledger_group":
        registry["entries"][0]["ledger_group"] = "UNKNOWN_GROUP"
    elif mutation == "premature_formal_use":
        registry["entries"][0]["formal_use_allowed"] = True
    else:  # pragma: no cover - the parameter list is the authority.
        raise AssertionError(f"unknown test mutation: {mutation}")
    validate = runpy.run_path(str(VALIDATOR_PATH))["validate_asset_registry"]
    dependencies, ledger_groups = authorities()

    with pytest.raises(AssertionError, match=message):
        validate(registry, dependencies, ledger_groups)
