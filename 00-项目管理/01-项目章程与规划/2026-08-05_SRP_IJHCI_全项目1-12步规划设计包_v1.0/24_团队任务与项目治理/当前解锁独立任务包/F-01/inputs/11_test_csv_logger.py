"""
Tests for csv_logger.py
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import importlib
csv_mod = importlib.import_module("05-通信协议.csv_logger")


class TestCSVLogger:
    def test_write_and_verify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            logger.open()
            for i in range(10):
                logger.write({
                    "timestamp": i * 0.1, "breath_score": 72.5,
                    "calm_index": 68.3, "breath_sync": 70.0,
                    "hrv_score": 65.0, "regularity_score": 60.0,
                    "depth_score": 55.0, "weather_intensity": 0.32,
                    "weather_trend": "weakening", "weather_type": "storm",
                    "rr": 14.2, "hr": 72.0, "rmssd": 45.2,
                    "breath_phase": "inhale", "guidance_prompt": "test",
                    "respiration_raw": 0.5, "ecg_raw": 0.1,
                })
            logger.close()
            stats = logger.stats()
            assert stats["rows"] == 10
            assert os.path.exists(stats["file"])
            assert stats["size_bytes"] > 0

    def test_csv_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = csv_mod.CSVLogger(output_dir=tmpdir, prefix="test")
            logger.open()
            logger.write({
                "timestamp": 0.0, "breath_score": 50, "calm_index": 50,
                "breath_sync": 50, "hrv_score": 50, "regularity_score": 50,
                "depth_score": 50, "weather_intensity": 0.5,
                "weather_trend": "stable", "weather_type": "storm",
                "rr": 14.0, "hr": 72.0, "rmssd": 45.0,
                "breath_phase": "exhale", "guidance_prompt": "",
                "respiration_raw": 0.0, "ecg_raw": 0.0,
            })
            logger.close()
            with open(logger.filename) as f:
                header = f.readline().strip()
                cols = header.split(",")
                assert "timestamp" in cols
                assert "breath_score" in cols
                assert "calm_index" in cols
                assert "weather_intensity" in cols
