"""Repository entry point for BigRun device preflight and calibration."""
from pathlib import Path
import sys

MODULES = Path(__file__).resolve().parents[1] / "modules"
sys.path.insert(0, str(MODULES))
sys.path.insert(0, str(MODULES / "acquisition"))

from bigrun.__main__ import main

if __name__ == "__main__":
    main(sys.argv[1:] or ["--help"])
