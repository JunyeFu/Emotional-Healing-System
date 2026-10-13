"""Fail-closed provenance gate for PDFs that may enter manuscript evidence."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "pdf_inventory.json"
REQUIRED = {
    "fn", "title", "authors", "year", "doi", "sha256",
    "source_url", "license_or_access_basis", "accessed_utc", "asset_role",
}


def main() -> int:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8-sig"))
    entries = payload.get("pdfs", [])
    physical = list(ROOT.rglob("*.pdf"))
    errors: list[str] = []

    if payload.get("total") != len(entries):
        errors.append(f"inventory total={payload.get('total')} entries={len(entries)}")
    if len(entries) != len(physical):
        errors.append(f"inventory entries={len(entries)} physical_pdfs={len(physical)}")

    physical_names = Counter(path.name for path in physical)
    inventory_names = Counter(str(entry.get("fn", "")) for entry in entries)
    if physical_names != inventory_names:
        errors.append("inventory filenames do not exactly match recursive physical PDFs")

    for index, entry in enumerate(entries, start=1):
        missing = sorted(REQUIRED - set(entry))
        empty = sorted(key for key in REQUIRED & set(entry) if not str(entry[key]).strip())
        if missing or empty:
            errors.append(
                f"entry {index} {entry.get('fn', '<unnamed>')}: "
                f"missing={missing or 'none'} empty={empty or 'none'}"
            )

    doi_counts = Counter(
        str(entry.get("doi", "")).strip().lower()
        for entry in entries
        if str(entry.get("doi", "")).strip()
    )
    ambiguous = sorted(doi for doi, count in doi_counts.items() if count > 1)
    if ambiguous:
        errors.append(
            "duplicate DOI identities require explicit parent/supplement asset roles: "
            + ",".join(ambiguous)
        )

    if errors:
        print("REFERENCE_PROVENANCE_BLOCKED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: reference provenance assets={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
