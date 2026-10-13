"""
Tests for udp_sender.py (v1.2 — 4 independent scores + device metadata)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import importlib
import math
udp = importlib.import_module("05-通信协议.udp_sender")


class TestBuildMessage:
    def test_all_fields_present(self):
        score_dict = {
            "timestamp": 1000.0,
            "breath_sync": 72.5, "breath_depth": 58.1,
            "hrv_coherence": 68.3, "eda_calm": 70.8,
            "calm_index": 67.4,
            "weather_intensity": 0.32, "weather_trend": "weakening",
            "dominant_domain": "eda_calm", "weather_type": "storm",
            "breath_phase": "inhale", "rr": 6.2,
            "hr": 78.0, "rmssd": 40.2,
            "respiration_raw": 0.5, "respiration_amplitude": 0.45,
            "breath_regularity_raw": 0.6,
            "ecg_raw": 0.15, "eda_raw": 7.2, "eda_tonic": 7.0,
            "guidance_prompt": "test",
        }
        meta = {
            "frame_id": 12,
            "devices": {"ecg": "mock", "resp": "mock", "eda": "mock"},
            "signal_quality": {"ecg": "mock", "resp": "mock", "eda": "mock"},
            "pipeline_latency_ms": 3.2,
            "buffer_backlog_frames": 0,
        }
        sources = {"breath": "mock", "cardiac": "mock", "eda": "mock"}
        msg = udp.build_message(score_dict, meta=meta, sources=sources)
        assert msg["version"] == "1.2"
        assert "scores" in msg
        assert "breath" in msg
        assert "cardiac" in msg
        assert "eda" in msg
        assert "weather" in msg
        assert "guidance" in msg
        assert "meta" in msg
        assert len(msg["scores"]) == 4
        assert msg["scores"]["breath_sync"] == 72.5
        assert msg["weather"]["intensity"] == 0.32
        assert msg["weather"]["type"] == "storm"
        assert msg["cardiac"]["hr"] == 78.0
        assert msg["eda"]["tonic"] == 7.0
        assert msg["breath"]["source"] == "mock"
        assert msg["cardiac"]["source"] == "mock"
        assert msg["eda"]["source"] == "mock"
        assert msg["meta"]["frame_id"] == 12

    def test_weather_type_enum_payload(self):
        for weather in ("storm", "heat", "snow", "fade"):
            msg = udp.build_message({"weather_type": weather})
            assert msg["weather"]["type"] == weather

    def test_payload_has_no_nan_defaults(self):
        msg = udp.build_message({})
        values = [
            msg["scores"]["breath_sync"],
            msg["scores"]["breath_depth"],
            msg["scores"]["hrv_coherence"],
            msg["scores"]["eda_calm"],
            msg["calm_index"],
            msg["weather"]["intensity"],
            msg["breath"]["rate"],
            msg["cardiac"]["hr"],
            msg["eda"]["tonic"],
        ]
        assert all(not math.isnan(v) for v in values)


class TestUDPSender:
    def test_send_to_localhost(self):
        sender = udp.UDPSender(targets=[("127.0.0.1", 50999)])
        score_dict = {
            "timestamp": 1000.0,
            "breath_sync": 72.5, "breath_depth": 58.1,
            "hrv_coherence": 68.3, "eda_calm": 70.8,
            "calm_index": 67.4,
            "weather_intensity": 0.32, "weather_trend": "weakening",
            "dominant_domain": "breath_sync", "weather_type": "storm",
            "breath_phase": "inhale", "rr": 6.2,
            "hr": 78.0, "rmssd": 40.2,
            "respiration_raw": 0.5, "respiration_amplitude": 0.45,
            "breath_regularity_raw": 0.6,
            "ecg_raw": 0.15, "eda_raw": 7.2, "eda_tonic": 7.0,
            "guidance_prompt": "test",
        }
        ok = sender.send(score_dict)
        assert ok, "Send failed"
        assert sender.stats()["frames_sent"] == 1
        sender.close()
