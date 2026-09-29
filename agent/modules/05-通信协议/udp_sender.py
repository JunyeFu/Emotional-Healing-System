"""
SRP UDP JSON Sender v1.2 — 4-dimension scoring model + device metadata.
=======================================================================
Sends 4-dimension scored data as JSON over UDP to TD and Unity.

Spec:
  Transport: UDP
  Encoding: JSON (UTF-8)
  Rate: 10 Hz
  Ports: TD:5005, Unity:5006

v1.2 adds per-signal source tracking, device connection status,
and signal quality metadata (see 真实设备方案.md).
"""

import json
import socket
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

UDP_TD_PORT = 5005
UDP_UNITY_PORT = 5006

DEFAULT_TARGETS = [
    ("127.0.0.1", UDP_TD_PORT),
    ("127.0.0.1", UDP_UNITY_PORT),
]


def build_message(
    score_dict: dict,
    meta: Optional[dict] = None,
    sources: Optional[dict[str, str]] = None,
) -> dict:
    """Build full UDP JSON message with 4 independent scores.

    Args:
        score_dict: Flat dict from ScoreFrame.to_dict().
        meta: Optional device metadata dict with keys:
              frame_id, devices, signal_quality, pipeline_latency_ms,
              buffer_backlog_frames.
        sources: Optional per-channel source strings, e.g.:
                 {"breath": "belt", "cardiac": "polar_h10", "eda": "wristband"}.
    """
    ts = score_dict.get("timestamp", time.time())
    sources = sources or {}
    meta = meta or {}

    # Compute circle_radius from respiration_depth (0=exhale, 1=inhale peak)
    resp_depth = score_dict.get("respiration_depth", 0.5)
    circle_radius = 0.08 + resp_depth * 0.17  # 0.08 → 0.25 range

    return {
        "version": "1.2",
        "timestamp": ts,

        # 4 independent scores
        "scores": {
            "breath_sync": score_dict.get("breath_sync", 50),
            "breath_depth": score_dict.get("breath_depth", 50),
            "hrv_coherence": score_dict.get("hrv_coherence", 50),
            "eda_calm": score_dict.get("eda_calm", 50),
        },

        # Calm index (top-level convenience)
        "calm_index": score_dict.get("calm_index", 50),

        # Weather composite
        "weather": {
            "type": score_dict.get("weather_type", "storm"),
            "composite": score_dict.get("calm_index", 50),
            "intensity": score_dict.get("weather_intensity", 0.5),
            "trend": score_dict.get("weather_trend", "stable"),
            "dominant": score_dict.get("dominant_domain", "—"),
        },

        # Breath domain
        "breath": {
            "phase": score_dict.get("breath_phase", "exhale"),
            "rate": score_dict.get("rr", 0),
            "amplitude": score_dict.get("respiration_amplitude", 0),
            "regularity_raw": score_dict.get("breath_regularity_raw", 0),
            "circle_radius": circle_radius,
            "source": sources.get("breath", "none"),
        },

        # Cardiac domain
        "cardiac": {
            "hr": score_dict.get("hr", 0),
            "rmssd": score_dict.get("rmssd", 0),
            "rr": score_dict.get("rr", 0),
            "ecg_raw": score_dict.get("ecg_raw", 0),
            "source": sources.get("cardiac", "none"),
        },

        # EDA domain (pure sympathetic)
        "eda": {
            "tonic": score_dict.get("eda_tonic", 0),
            "raw": score_dict.get("eda_raw", 0),
            "source": sources.get("eda", "none"),
        },

        # Guidance
        "guidance": {
            "prompt": score_dict.get("guidance_prompt", ""),
            "target_breath_rate": 10,
        },

        # Device metadata (v1.2)
        "meta": {
            "frame_id": meta.get("frame_id", 0),
            "devices": meta.get("devices", {}),
            "signal_quality": meta.get("signal_quality", {}),
            "pipeline_latency_ms": meta.get("pipeline_latency_ms", 0.0),
            "buffer_backlog_frames": meta.get("buffer_backlog_frames", 0),
        },
    }


class UDPSender:
    """Sends UDP JSON messages to multiple targets (TD + Unity)."""

    def __init__(self, targets: list[tuple[str, int]] | None = None):
        self.targets = targets or DEFAULT_TARGETS
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.frame_count = 0
        self.error_count = 0

    def send(self, score_dict: dict, meta: Optional[dict] = None,
             sources: Optional[dict[str, str]] = None) -> bool:
        message = build_message(score_dict, meta=meta, sources=sources)
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")

        all_ok = True
        for host, port in self.targets:
            try:
                self.sock.sendto(payload, (host, port))
            except OSError as e:
                logger.warning(f"UDP send to {host}:{port} failed: {e}")
                self.error_count += 1
                all_ok = False

        self.frame_count += 1
        return all_ok

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

    def stats(self) -> dict:
        return {
            "frames_sent": self.frame_count,
            "errors": self.error_count,
            "targets": [f"{h}:{p}" for h, p in self.targets],
        }


if __name__ == "__main__":
    import sys, os
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

    sender = UDPSender()
    print(f"UDP Sender v1.2 self-test: {len(sender.targets)} targets")
    for i in range(5):
        test_frame = {
            "timestamp": time.time(),
            "breath_sync": 72.5, "breath_depth": 58.1,
            "hrv_coherence": 68.3, "eda_calm": 70.8,
            "calm_index": 67.4,
            "weather_intensity": 0.33, "weather_trend": "weakening",
            "dominant_domain": "breath_sync", "weather_type": "storm",
            "breath_phase": "inhale", "rr": 6.2,
            "hr": 78.0, "rmssd": 40.2,
            "respiration_amplitude": 0.45, "breath_regularity_raw": 0.6,
            "ecg_raw": 0.15, "eda_raw": 7.2, "eda_tonic": 7.0,
            "guidance_prompt": "慢慢吸气...4秒",
        }
        test_meta = {
            "frame_id": i,
            "devices": {"ecg": "connected", "resp": "connected", "eda": "no_signal"},
            "signal_quality": {"ecg_contact": True, "resp_quality": 0.87, "eda_contact": False},
            "pipeline_latency_ms": 3.2,
            "buffer_backlog_frames": 0,
        }
        test_sources = {"breath": "belt", "cardiac": "polar_h10", "eda": "none"}
        ok = sender.send(test_frame, meta=test_meta, sources=test_sources)
        print(f"  Frame {i + 1}: {'OK' if ok else 'FAIL'}")
        time.sleep(0.1)

    print(f"\nStats: {sender.stats()}")
    sender.close()
