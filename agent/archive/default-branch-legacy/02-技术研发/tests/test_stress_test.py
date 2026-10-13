"""
Tests for stress_test.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import importlib


class TestStressTestModule:
    def test_module_imports(self):
        st = importlib.import_module("stress_test")
        assert st.WEATHER_CYCLE == ["storm", "heat", "snow", "fade"]
        assert st.SECONDS_PER_SEGMENT == 15
        assert st.FRAME_RATE == 10
        assert st.EXPECTED_FRAMES == 600


class TestSegmentStats:
    def test_averages(self):
        st = importlib.import_module("stress_test")
        stats = st.SegmentStats(weather_type="storm")
        stats.breath_sync_scores = [70.0, 80.0, 90.0]
        stats.breath_depth_scores = [60.0, 70.0, 80.0]
        stats.hrv_coherence_scores = [50.0, 60.0, 70.0]
        stats.eda_calm_scores = [40.0, 50.0, 60.0]
        stats.calm_indices = [60.0, 70.0, 80.0]
        stats.weather_intensities = [0.3, 0.2, 0.1]
        assert stats.avg_dim_score("breath_sync") == 80.0
        assert stats.avg_dim_score("breath_depth") == 70.0
        assert stats.avg_dim_score("hrv_coherence") == 60.0
        assert stats.avg_dim_score("eda_calm") == 50.0
        assert stats.avg_calm_index() == 70.0
        assert abs(stats.avg_intensity() - 0.2) < 1e-9, f"Expected ~0.2 got {stats.avg_intensity()}"

    def test_empty_stats_returns_zero(self):
        st = importlib.import_module("stress_test")
        stats = st.SegmentStats(weather_type="fade")
        assert stats.avg_dim_score("breath_sync") == 0.0
        assert stats.avg_dim_score("breath_depth") == 0.0
        assert stats.avg_dim_score("hrv_coherence") == 0.0
        assert stats.avg_dim_score("eda_calm") == 0.0
        assert stats.avg_calm_index() == 0.0
