"""
SRP CSV Logger (Sprint 0)
===========================
Records scored physiological frames to a structured CSV file
for offline analysis by the experiment team.

File naming: sim_YYYYMMDD_HHMMSS_microseconds.csv or a formal session prefix.
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO
import logging

logger = logging.getLogger(__name__)


# ── CSV Column Order (matches UDP fields) ──────────────────────────────────

CSV_COLUMNS = [
    "timestamp",
    "breath_sync",
    "breath_depth",
    "hrv_coherence",
    "eda_calm",
    "calm_index",
    "weather_intensity",
    "weather_trend",
    "dominant_domain",
    "weather_type",
    "rr",
    "hr",
    "rmssd",
    "respiration_raw",
    "respiration_amplitude",
    "breath_regularity_raw",
    "ecg_raw",
    "eda_raw",
    "eda_tonic",
    "breath_phase",
    "respiration_depth",
    "guidance_prompt",
]


# ── CSV Logger ─────────────────────────────────────────────────────────────

class CSVLogger:
    """Records ScoreFrame data to a CSV file with column headers."""

    def __init__(self, output_dir: str | None = None, prefix: str = "sim"):
        """Initialize CSV logger.

        Args:
            output_dir: Directory for CSV files. Defaults to 03-测试与实验/实验数据/
            prefix: File prefix ("sim" for simulated, session ID for formal runs)
        """
        if output_dir is None:
            project_root = Path(__file__).resolve().parents[2]
            output_dir = project_root / "03-测试与实验" / "实验数据"
        self.output_dir = os.path.abspath(os.fspath(output_dir))
        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.filename = os.path.join(self.output_dir, f"{prefix}_{timestamp}.csv")
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.DictWriter] = None
        self.row_count = 0

    def open(self):
        """Open CSV file and write headers."""
        self._file = open(self.filename, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=CSV_COLUMNS)
        self._writer.writeheader()
        logger.info(f"CSV log opened: {self.filename}")

    def write(self, score_dict: dict):
        """Write one scored frame to CSV.

        Args:
            score_dict: ScoreFrame.to_dict() output.
        """
        if self._writer is None:
            raise RuntimeError("CSVLogger not opened. Call open() first.")

        expected = set(CSV_COLUMNS)
        actual = set(score_dict)
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        if missing or unknown:
            raise ValueError(
                "CSV_SCHEMA_MISMATCH: "
                f"missing={missing or 'none'} unknown={unknown or 'none'}"
            )
        self._writer.writerow({col: score_dict[col] for col in CSV_COLUMNS})
        self.row_count += 1

    def close(self):
        """Flush and close the CSV file."""
        if self._file:
            self._file.flush()
            self._file.close()
            self._file = None
            self._writer = None
            logger.info(f"CSV log closed: {self.filename} ({self.row_count} rows)")

    def stats(self) -> dict:
        """Return logger statistics."""
        return {
            "file": self.filename,
            "rows": self.row_count,
            "size_bytes": os.path.getsize(self.filename) if os.path.exists(self.filename) else 0,
        }


# ── Self-test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = CSVLogger(output_dir=tmpdir, prefix="test")
        logger.open()

        for i in range(5):
            logger.write({
                "timestamp": time.time() + i * 0.1,
                "breath_sync": 70.0,
                "breath_depth": 55.0,
                "hrv_coherence": 65.0,
                "eda_calm": 60.0,
                "calm_index": 68.3,
                "weather_intensity": 0.32,
                "weather_trend": "weakening",
                "dominant_domain": "breath_sync",
                "weather_type": "storm",
                "rr": 14.2,
                "hr": 72.0,
                "rmssd": 45.2,
                "respiration_raw": 0.65,
                "respiration_amplitude": 0.5,
                "breath_regularity_raw": 0.8,
                "ecg_raw": 0.12,
                "eda_raw": 7.2,
                "eda_tonic": 7.0,
                "breath_phase": "inhale",
                "respiration_depth": 0.5,
                "guidance_prompt": "慢慢吸气...4秒",
            })

        logger.close()
        print(f"CSV Logger self-test: {logger.stats()}")

        # Verify file content
        with open(logger.filename, "r") as f:
            lines = f.readlines()
            print(f"Header: {lines[0].strip()}")
            print(f"Rows: {len(lines) - 1}")
