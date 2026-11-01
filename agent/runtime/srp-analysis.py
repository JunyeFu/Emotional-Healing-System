"""Run SRP analysis from any working directory using the repository modules."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'modules'))
from srp_analysis.__main__ import main

if __name__ == '__main__':
    main()
