#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def assert_valid(instance, schema_path):
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(
        schema, format_checker=FormatChecker()
    ).iter_errors(instance))
    if errors:
        raise AssertionError("\n".join(e.message for e in errors))


def main():
    manifest = yaml.safe_load(
        (ROOT / "config" / "experiment_manifest.example.yaml").read_text(encoding="utf-8")
    )
    assert_valid(manifest, ROOT / "contracts" / "experiment-manifest.schema.json")

    protocol = yaml.safe_load((ROOT / "config" / "protocols.v1.yaml").read_text(encoding="utf-8"))
    assert protocol["timing"]["module_total_s"] == (
        protocol["timing"]["demo_s"]
        + protocol["timing"]["closed_loop_s"]
        + protocol["timing"]["lock_transition_s"]
    )
    assert protocol["modules"]["fade"]["formal_blocker"] is True

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "generate_randomization.py"),
                "--n", "104", "--seed", "20260805", "--output-dir", td,
            ],
            check=True,
        )
        schedule = Path(td) / "allocation_schedule.csv"
        assert schedule.exists()
        assert len(schedule.read_text(encoding="utf-8-sig").splitlines()) == 105

    print("PACKAGE VERIFICATION PASS")


if __name__ == "__main__":
    main()
