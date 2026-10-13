"""Build deterministic hashes for UP-01 through UP-12 evidence references."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


UPGRADE = Path(__file__).resolve().parent
GOVERNANCE = UPGRADE.parent
PROJECT_ROOT = GOVERNANCE.parents[3]
REGISTRY = UPGRADE / "upgrade_subdeliveries_v1.0.csv"
OUTPUT = UPGRADE / "upgrade_evidence_manifest_v1.0.json"


def resolve_ref(reference: str) -> Path:
    prefix, relative = reference.split(":", 1)
    roots = {"audit": UPGRADE, "governance": GOVERNANCE, "project": PROJECT_ROOT}
    if prefix not in roots or not relative or Path(relative).is_absolute():
        raise ValueError(f"invalid evidence reference: {reference}")
    root = roots[prefix].resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError(f"missing evidence reference: {reference}")
    return path


def main() -> None:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    entries = {}
    for row in rows:
        refs = []
        for reference in row["evidence_refs"].split("|"):
            path = resolve_ref(reference)
            refs.append(
                {
                    "reference": reference,
                    "byte_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                }
            )
        entries[row["subdelivery_id"]] = refs
    payload = {"schema_version": "1.0", "entries": entries}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUTPUT.name}; upgrades={len(entries)}")


if __name__ == "__main__":
    main()
