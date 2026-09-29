"""CSV evidence-contract tests."""

import csv
import importlib
import os
import sys
import tempfile

import pytest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
csv_mod = importlib.import_module("05-通信协议.csv_logger")


def score_row(timestamp: float = 0.0) -> dict:
    return {
        "timestamp": timestamp,
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
        "respiration_raw": 0.5,
        "respiration_amplitude": 0.4,
        "breath_regularity_raw": 0.8,
        "ecg_raw": 0.1,
        "eda_raw": 7.2,
        "eda_tonic": 7.0,
        "breath_phase": "inhale",
        "respiration_depth": 0.5,
        "guidance_prompt": "test",
    }


class TestCSVLogger:
    def test_score_frame_fields_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            logger.open()
            expected = score_row(1.25)
            logger.write(expected)
            logger.close()

            with open(logger.filename, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                actual = next(reader)
            assert reader.fieldnames == csv_mod.CSV_COLUMNS
            assert set(actual) == set(expected)
            assert actual["breath_depth"] == "55.0"
            assert actual["hrv_coherence"] == "65.0"
            assert actual["eda_calm"] == "60.0"
            assert actual["eda_tonic"] == "7.0"

    @pytest.mark.parametrize("mutation", ["missing", "unknown"])
    def test_schema_drift_fails_closed(self, mutation):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            logger.open()
            row = score_row()
            if mutation == "missing":
                row.pop("eda_calm")
            else:
                row["retired_score"] = 50
            with pytest.raises(ValueError, match="CSV_SCHEMA_MISMATCH"):
                logger.write(row)
            logger.close()

    def test_file_names_do_not_collide_within_one_second(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            second = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            assert first.filename != second.filename
