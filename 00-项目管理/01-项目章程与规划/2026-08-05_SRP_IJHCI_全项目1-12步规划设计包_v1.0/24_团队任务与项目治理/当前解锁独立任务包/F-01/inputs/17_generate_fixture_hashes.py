"""Generate deterministic SHA-256 evidence for F-01 JSON fixtures."""

from hashlib import sha256
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "fixture_hashes.sha256"


def main() -> None:
    lines = []
    for path in sorted((ROOT / "fixtures").rglob("*.json")):
        digest = sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    print(f"WROTE: {OUTPUT}; fixtures={len(lines)}")


if __name__ == "__main__":
    main()
