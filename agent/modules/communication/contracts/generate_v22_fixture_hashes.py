"""Generate deterministic SHA-256 evidence for F-05 v2.2 fixtures."""

from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "fixture_hashes_v2.2.sha256"
FIXTURE_ROOTS = (ROOT / "fixtures-v2.2", ROOT / "consumer-fixtures" / "v2.2")


def _canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def main() -> None:
    paths = sorted(
        path
        for root in FIXTURE_ROOTS
        for suffix in ("*.json", "*.jsonl")
        for path in root.rglob(suffix)
    )
    lines = [
        f"{sha256(_canonical_bytes(path)).hexdigest()}  {path.relative_to(ROOT).as_posix()}"
        for path in paths
    ]
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    print(f"WROTE: {OUTPUT}; fixtures={len(lines)}")


if __name__ == "__main__":
    main()
