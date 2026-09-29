"""
Tests for mock_data.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import importlib
mock = importlib.import_module("01-数据采集.mock_data")


class TestMockConfig:
    def test_defaults(self):
        cfg = mock.MockConfig()
        assert cfg.breath_rate_hz == 0.2
        assert cfg.hr_bpm == 80.0
        assert cfg.frame_rate == 10.0

    def test_custom_weather(self):
        cfg = mock.MockConfig(weather_type="heat", weather_intensity_base=0.8)
        assert cfg.weather_type == "heat"
        assert cfg.weather_intensity_base == 0.8


class TestMockFrame:
    def test_to_dict(self):
        f = mock.MockFrame(0.0, 0.5, 0.1, 8.0, 0.04, 34.0, "inhale", "test", "storm", 0.5)
        d = f.to_dict()
        assert "timestamp" in d
        assert d["breath_phase"] == "inhale"
        assert d["weather_type"] == "storm"
        assert "eda_raw" in d
        assert "acc_magnitude" in d
        assert "temp_skin" in d


class TestGenerateFrames:
    def test_frame_count(self):
        cfg = mock.MockConfig(frame_rate=10.0)
        frames = mock.generate_frame_list(duration=2.0, cfg=cfg)
        assert len(frames) == 20
        assert all(len(frame.ecg_samples) == 13 for frame in frames)
        native_timestamps = [ts for frame in frames for ts, _ in frame.ecg_samples]
        assert all(
            later > earlier
            for earlier, later in zip(native_timestamps, native_timestamps[1:])
        )

    def test_breath_phases_present(self):
        frames = mock.generate_frame_list(duration=12.0)
        phases = {f.breath_phase for f in frames}
        assert "inhale" in phases
        assert "exhale" in phases

    def test_values_in_range(self):
        frames = mock.generate_frame_list(duration=5.0)
        for f in frames:
            assert -1.0 <= f.respiration_raw <= 1.5
            assert -0.5 <= f.ecg_raw <= 1.5


class TestWeatherBreathingConfig:
    def test_all_weathers_have_config(self):
        for w in ["storm", "heat", "snow", "fade"]:
            assert w in mock.WEATHER_BREATHING_CONFIG, f"Missing config for {w}"

    def test_for_weather_factory(self):
        cfg = mock.MockConfig.for_weather("heat")
        assert cfg.weather_type == "heat"
        assert cfg.inhale_duration == 3.0
        assert cfg.exhale_duration == 6.0
        assert cfg.hold_duration == 0.0
        assert cfg.hr_bpm == 82.5

    def test_for_weather_unknown_falls_back(self):
        cfg = mock.MockConfig.for_weather("nonexistent")
        assert cfg.weather_type == "nonexistent"
        assert cfg.inhale_duration == 4.0  # storm default

    def test_storm_has_hold_phase(self):
        cfg = mock.MockConfig.for_weather("storm")
        frames = mock.generate_frame_list(duration=12.0, cfg=cfg)
        phases = {f.breath_phase for f in frames}
        assert "hold" in phases

    def test_heat_no_hold_phase(self):
        cfg = mock.MockConfig.for_weather("heat")
        frames = mock.generate_frame_list(duration=9.0, cfg=cfg)
        phases = {f.breath_phase for f in frames}
        assert "hold" not in phases

    def test_per_weather_frame_counts(self):
        for w in ["storm", "heat", "snow", "fade"]:
            cfg = mock.MockConfig.for_weather(w)
            frames = mock.generate_frame_list(duration=15.0, cfg=cfg)
            assert len(frames) == 150, f"{w}: expected 150, got {len(frames)}"
