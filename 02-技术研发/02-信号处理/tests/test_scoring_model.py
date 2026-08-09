"""
Tests for scoring_model.py (v2.0 — 4 independent scores)
"""
import sys, os
from dataclasses import dataclass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import importlib
sm = importlib.import_module("02-信号处理.scoring_model")


@dataclass
class PF:
    timestamp: float = 0
    rr: float = 10.0
    respiration_amplitude: float = 0.5
    breath_regularity: float = 1.0
    hr: float = 70.0
    rmssd: float = 50.0
    eda_tonic: float = 8.0
    respiration_raw: float = 0.5
    ecg_raw: float = 0.1
    eda_raw: float = 8.0


class TestScoringModel:
    def test_default_returns_neutral(self):
        model = sm.ScoringModel()
        result = model.score(None)
        assert result.breath_sync == 50
        assert result.calm_index == 50
        assert result.weather_intensity == 0.5

    def test_perfect_scoring(self):
        model = sm.ScoringModel()
        pf = PF(rr=10.0, respiration_amplitude=0.5, breath_regularity=1.0,
                hr=70.0, rmssd=50.0)
        result = model.score(pf)
        assert result.breath_sync > 80, f"Expected >80 got {result.breath_sync}"
        assert result.calm_index > 50
        assert 0 <= result.weather_intensity <= 1

    def test_poor_scoring(self):
        model = sm.ScoringModel()
        pf = PF(rr=25.0, respiration_amplitude=0.1, breath_regularity=0.2,
                hr=110.0, rmssd=10.0)
        result = model.score(pf)
        assert result.breath_sync < 40, f"Expected <40 got {result.breath_sync}"

    def test_value_ranges(self):
        model = sm.ScoringModel()
        pf = PF(rr=12.0, respiration_amplitude=0.4, breath_regularity=0.6,
                hr=78.0, rmssd=35.0)
        result = model.score(pf)
        assert 0 <= result.breath_sync <= 100
        assert 0 <= result.calm_index <= 100
        assert 0 <= result.weather_intensity <= 1
        # All 4 scores should be present
        assert 0 <= result.breath_depth <= 100
        assert 0 <= result.hrv_coherence <= 100
        assert 0 <= result.eda_calm <= 100

    def test_score_list_has_4_items(self):
        model = sm.ScoringModel()
        pf = PF()
        result = model.score(pf)
        sl = result.score_list()
        assert len(sl) == 4, f"Expected 4 scores got {len(sl)}: {sl}"
        assert sl[0][0] == "Breath Sync"
        assert sl[-1][0] == "EDA Calm"

    def test_weather_trend_compares_with_previous_frame(self):
        model = sm.ScoringModel()
        improving = model.score(PF(
            rr=10.0, respiration_amplitude=0.5,
            rmssd=70.0, eda_tonic=8.0,
        ))
        worsening = model.score(PF(
            rr=30.0, respiration_amplitude=0.01,
            rmssd=1.0, eda_tonic=12.0,
        ))
        assert improving.weather_trend == "weakening"
        assert worsening.weather_trend == "intensifying"


class TestPerWeatherScoring:
    def test_all_weathers_have_scoring_presets(self):
        for w in ["storm", "heat", "snow", "fade"]:
            assert w in sm.WEATHER_SCORING_PRESETS, f"Missing preset for {w}"

    def test_scoring_config_for_weather(self):
        cfg = sm.ScoringConfig.for_weather("heat")
        assert cfg.target_amplitude == 0.6
        assert round(cfg.target_rr, 2) == 6.67

    def test_different_weathers_produce_different_scores(self):
        pf = PF(rr=6.0, respiration_amplitude=0.5, breath_regularity=0.8,
                hr=75.0, rmssd=45.0)
        storm_model = sm.ScoringModel(cfg=sm.ScoringConfig.for_weather("storm"))
        heat_model = sm.ScoringModel(cfg=sm.ScoringConfig.for_weather("heat"))
        storm_result = storm_model.score(pf)
        heat_result = heat_model.score(pf)
        assert storm_result.breath_sync != heat_result.breath_sync

    def test_scoring_model_with_weather_type(self):
        model = sm.ScoringModel(cfg=sm.ScoringConfig.for_weather("snow"))
        pf = PF(rr=6.0, respiration_amplitude=0.4, breath_regularity=0.7,
                hr=65.0, rmssd=50.0)
        result = model.score(pf)
        assert 0 <= result.breath_sync <= 100
