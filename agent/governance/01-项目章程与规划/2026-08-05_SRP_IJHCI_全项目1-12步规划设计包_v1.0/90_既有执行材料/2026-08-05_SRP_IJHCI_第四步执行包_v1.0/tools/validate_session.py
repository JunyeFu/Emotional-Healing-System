#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(instance, schema, label: str):
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path))}: {e.message}" for e in errors]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_dir")
    parser.add_argument("--package-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()

    session_dir = Path(args.session_dir)
    package_root = Path(args.package_root)
    report = {"hard_failures": [], "warnings": [], "metrics": {}}

    manifest_path = session_dir / "manifest.yaml"
    events_path = session_dir / "events" / "events.jsonl"
    if not manifest_path.exists():
        report["hard_failures"].append("manifest.yaml missing")
    if not events_path.exists():
        report["hard_failures"].append("events/events.jsonl missing")

    if not report["hard_failures"]:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest_schema = load_json(package_root / "contracts" / "experiment-manifest.schema.json")
        report["hard_failures"].extend(validate(manifest, manifest_schema, "manifest"))

        event_schema = load_json(package_root / "contracts" / "event-envelope.schema.json")
        events = []
        for line_no, line in enumerate(events_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                report["hard_failures"].append(f"events line {line_no}: invalid JSON: {exc}")
                continue
            events.append(event)
            report["hard_failures"].extend(validate(event, event_schema, f"events line {line_no}"))

        if events:
            seqs = [e["sequence_number"] for e in events if "sequence_number" in e]
            if any(b <= a for a, b in zip(seqs, seqs[1:])):
                report["hard_failures"].append("sequence_number is not strictly increasing")
            expected_pid = manifest.get("participant_id")
            expected_sid = manifest.get("session_id")
            for i, e in enumerate(events, start=1):
                if e.get("participant_id") != expected_pid or e.get("session_id") != expected_sid:
                    report["hard_failures"].append(f"event {i}: participant/session mismatch")

            module_starts = [
                e for e in events
                if e.get("event_type") == "module_phase"
                and e.get("payload", {}).get("phase") == "demo"
                and e.get("payload", {}).get("action") == "start"
            ]
            report["metrics"]["module_demo_start_count"] = len(module_starts)
            if len(module_starts) != 4:
                report["warnings"].append("expected 4 module demo starts")

        if manifest.get("study_mode") == "formal" and manifest.get("mock_input"):
            report["hard_failures"].append("formal session cannot use mock input")

    report["status"] = "FAIL" if report["hard_failures"] else "PASS"
    output = session_dir / "qc_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if report["hard_failures"] else 0)


if __name__ == "__main__":
    main()
