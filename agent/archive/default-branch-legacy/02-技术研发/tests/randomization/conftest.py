from __future__ import annotations

from pathlib import Path
import sys


TECH_ROOT = Path(__file__).resolve().parents[2]
RANDOMIZATION_ROOT = TECH_ROOT / "08-随机化"

for path in (TECH_ROOT, RANDOMIZATION_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
