"""
SRP Signal Pipeline (Sprint 0 v0.3)
====================================
Processes raw multi-sensor signals through NeuroKit2 and custom estimators
to extract physiological features for independent per-signal scoring.

Pipeline flow:
  Raw frames → buffering → NeuroKit2 / custom processing → feature extraction

Signal domains:
  - Respiration: RSP → RR, amplitude, regularity, phase
  - Cardiac:     ECG → HR, RMSSD (HRV)
  - EDA:         Skin conductance → tonic level
  - ACC:         Motion → stillness index
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Iterable, Optional
from dataclasses import dataclass
from collections import deque
import warnings
import numpy as np
import neurokit2 as nk

warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")
warnings.filterwarnings("ignore", message="Too few peaks detected", module="neurokit2")


BUFFER_SIZE = 300
PROCESSING_WINDOW = 100
EDA_WINDOW = 40    # 4 seconds for tonic extraction
ACC_WINDOW = 10    # 1 second for motion RMS


@dataclass
class ProcessedFrame:
    """Extracted physiological features from a sliding window of raw signals."""
    timestamp: float

    # Respiratory features
    rr: float = 0.0                      # breaths/min
    respiration_amplitude: float = 0.0   # normalized depth (RMS)
    breath_regularity: float = 0.0       # 0=irregular, 1=periodic

    # Cardiac features
    hr: float = 0.0                      # BPM
    rmssd: float = 0.0                   # HRV index (ms)

    # EDA features
    eda_tonic: float = 0.0               # skin conductance level (μS)

    # Motion features
    motion_index: float = 0.0            # body movement (g RMS)

    # Raw snapshots (for logging)
    respiration_raw: float = 0.0
    ecg_raw: float = 0.0
    eda_raw: float = 0.0
    acc_magnitude: float = 0.0
    temp_skin: float = 0.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "rr": round(self.rr, 2),
            "respiration_amplitude": round(self.respiration_amplitude, 4),
            "breath_regularity": round(self.breath_regularity, 4),
            "hr": round(self.hr, 1),
            "rmssd": round(self.rmssd, 1),
            "eda_tonic": round(self.eda_tonic, 2),
            "motion_index": round(self.motion_index, 4),
            "respiration_raw": round(self.respiration_raw, 4),
            "ecg_raw": round(self.ecg_raw, 4),
            "eda_raw": round(self.eda_raw, 4),
            "acc_magnitude": round(self.acc_magnitude, 4),
            "temp_skin": round(self.temp_skin, 2),
        }


class SignalPipeline:
    """Rolling-buffer processor for multi-sensor physiological signals."""

    def __init__(self, buffer_size: int = BUFFER_SIZE):
        self.resp_buffer: deque[float] = deque(maxlen=buffer_size)
        # ECG is intentionally separate from the 10 Hz coordination buffers.
        # Thirty seconds at 130 Hz preserves R-peak timing for HR/RMSSD.
        self.ecg_native_buffer: deque[tuple[float, float]] = deque(maxlen=3900)
        self.eda_buffer: deque[float] = deque(maxlen=buffer_size)
        self.acc_buffer: deque[float] = deque(maxlen=buffer_size)
        self.t_buffer: deque[float] = deque(maxlen=buffer_size)

        self._last_rr = 14.0
        self._last_hr: Optional[float] = None
        self._last_rmssd: Optional[float] = None
        self._last_resp_amp = 0.5
        self._last_eda_tonic = 8.0
        self._last_motion = 0.04
        self.last_status = "warmup"
        self.last_invalid_reasons: tuple[str, ...] = ()

    def feed(self, timestamp: float, respiration: Optional[float], ecg: Optional[float],
             eda: Optional[float] = None, acc_mag: Optional[float] = None,
             temp_skin: Optional[float] = None,
             ecg_samples: Optional[Iterable[tuple[float, float]]] = None,
             ) -> Optional[ProcessedFrame]:
        """Feed one multi-sensor frame into the pipeline.

        Returns ProcessedFrame after warmup, or None during warmup.
        """
        reasons: list[str] = []
        self.t_buffer.append(timestamp)
        if respiration is None or not np.isfinite(respiration):
            reasons.append("resp_missing")
        else:
            self.resp_buffer.append(float(respiration))

        native_batch = list(ecg_samples or ())
        for sample_ts, sample_value in native_batch:
            if np.isfinite(sample_ts) and np.isfinite(sample_value):
                self.ecg_native_buffer.append((float(sample_ts), float(sample_value)))
        if not native_batch:
            reasons.append("ecg_native_missing")

        if eda is None or not np.isfinite(eda):
            reasons.append("eda_missing")
        else:
            self.eda_buffer.append(float(eda))
        if acc_mag is not None and np.isfinite(acc_mag):
            self.acc_buffer.append(float(acc_mag))

        if len(self.resp_buffer) < PROCESSING_WINDOW:
            self.last_status = "warmup"
            self.last_invalid_reasons = tuple(sorted(set(reasons)))
            return None

        # --- Respiratory processing ---
        resp_arr = np.array(self.resp_buffer, dtype=np.float64)

        rr_val = self._autocorr_resp_rate(resp_arr)
        if rr_val is None:
            reasons.append("resp_rate_unavailable")
        else:
            self._last_rr = rr_val
        resp_amp = float(np.std(resp_arr[-PROCESSING_WINDOW:]))
        self._last_resp_amp = resp_amp
        regularity = self._estimate_regularity(resp_arr[-PROCESSING_WINDOW:])

        # --- Cardiac processing ---
        try:
            hrv = self._extract_hrv(tuple(self.ecg_native_buffer))
        except Exception:
            hrv = None
        if hrv is None:
            reasons.append("ecg_hrv_unavailable")
            hr_val = None
            rmssd_val = None
        else:
            hr_val, rmssd_val = hrv
            self._last_hr, self._last_rmssd = hrv

        # --- EDA processing: tonic extraction via moving average ---
        if self.eda_buffer:
            eda_arr = np.array(self.eda_buffer, dtype=np.float64)
            window_n = min(EDA_WINDOW, len(eda_arr))
            eda_tonic = float(np.mean(eda_arr[-window_n:]))
            self._last_eda_tonic = eda_tonic
        else:
            eda_tonic = None

        # --- Motion processing: RMS of recent ACC ---
        if self.acc_buffer:
            acc_arr = np.array(self.acc_buffer, dtype=np.float64)
            window_n = min(ACC_WINDOW, len(acc_arr))
            motion_rms = float(np.sqrt(np.mean(acc_arr[-window_n:] ** 2)))
            self._last_motion = motion_rms
        else:
            motion_rms = 0.0

        if reasons or rr_val is None or hr_val is None or rmssd_val is None or eda_tonic is None:
            self.last_status = "invalid"
            self.last_invalid_reasons = tuple(sorted(set(reasons)))
            return None

        self.last_status = "valid"
        self.last_invalid_reasons = ()

        return ProcessedFrame(
            timestamp=timestamp,
            rr=rr_val,
            respiration_amplitude=resp_amp,
            breath_regularity=regularity,
            hr=hr_val,
            rmssd=rmssd_val,
            eda_tonic=eda_tonic,
            motion_index=motion_rms,
            respiration_raw=float(respiration),
            ecg_raw=float(ecg if ecg is not None else native_batch[-1][1]),
            eda_raw=float(eda),
            acc_magnitude=float(acc_mag or 0.0),
            temp_skin=float(temp_skin) if temp_skin is not None else float("nan"),
        )

    # ── Cardiac: native-rate peak detector ───────────────────────────────

    def _extract_hrv(
        self, ecg_samples: tuple[tuple[float, float], ...]
    ) -> Optional[tuple[float, float]]:
        """Extract HR/RMSSD only from timestamped native-rate ECG samples."""
        if len(ecg_samples) < 130 * 3:
            return None
        timestamps = np.array([sample[0] for sample in ecg_samples], dtype=np.float64)
        ecg_arr = np.array([sample[1] for sample in ecg_samples], dtype=np.float64)
        if np.any(np.diff(timestamps) <= 0):
            return None

        centered = ecg_arr - np.mean(ecg_arr)
        threshold = np.std(centered) * 0.4
        if threshold <= 0:
            return None

        # Native timestamps enforce the 300 ms refractory interval even when
        # device sampling has small jitter.
        peaks: list[int] = []
        for i in range(1, len(centered) - 1):
            if centered[i] <= threshold:
                continue
            if centered[i] <= centered[i - 1] or centered[i] < centered[i + 1]:
                continue
            if peaks and (timestamps[i] - timestamps[peaks[-1]]) < 0.3:
                if centered[i] > centered[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)

        if len(peaks) < 3:
            return None

        rr_ms = np.diff(timestamps[peaks]) * 1000.0
        hr_val = float(60000.0 / np.mean(rr_ms))
        rmssd_val = float(np.sqrt(np.mean(np.diff(rr_ms) ** 2)))
        if not (40.0 <= hr_val <= 120.0 and 0.0 <= rmssd_val <= 200.0):
            return None

        return hr_val, rmssd_val

    # ── Fallback estimators ──────────────────────────────────────────────

    def _autocorr_resp_rate(self, signal: np.ndarray) -> Optional[float]:
        """Detect respiration rate via autocorrelation peak.

        Robust to asymmetric waveforms (non-sinusoidal inhale/hold/exhale)
        where zero-crossing and NK2 peak detectors fail. Returns bpm or None.
        """
        n = len(signal)
        if n < 30:
            return None

        centered = signal - np.mean(signal)
        acorr = np.correlate(centered, centered, mode="full")
        acorr = acorr[len(acorr) // 2:]
        if acorr[0] < 1e-10:
            return None
        acorr = acorr / acorr[0]

        # Search for first major peak in physiologically plausible range:
        # 4 bpm (15s周期 = 150 samples) to 30 bpm (2s周期 = 20 samples)
        min_lag = max(int(10 * 60.0 / 30.0), 10)   # 20 samples
        max_lag = min(int(10 * 60.0 / 4.0), n - 2)  # 150 samples
        threshold = 0.25  # minimum autocorrelation for a valid peak

        best_lag = None
        for lag in range(min_lag, max_lag):
            if acorr[lag] > threshold and acorr[lag] > acorr[lag - 1] and acorr[lag] >= acorr[lag + 1]:
                best_lag = lag
                break

        if best_lag is None:
            return None

        return 600.0 / best_lag  # 10 Hz * 60 s / lag_samples

    def _estimate_regularity(self, signal: np.ndarray) -> float:
        centered = signal - np.mean(signal)
        autocorr = np.correlate(centered, centered, mode="full")
        autocorr = autocorr[len(autocorr) // 2:]
        autocorr = autocorr / (autocorr[0] + 1e-10)
        peaks_idx = np.where(
            (autocorr[1:-1] > autocorr[:-2]) &
            (autocorr[1:-1] > autocorr[2:])
        )[0] + 1
        if len(peaks_idx) == 0:
            return 0.5
        return float(np.clip(autocorr[peaks_idx[0]], 0, 1))


# ── Self-test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _parent not in sys.path:
        sys.path.insert(0, _parent)
    import importlib
    _mock = importlib.import_module("01-数据采集.mock_data")
    MockConfig = _mock.MockConfig
    generate_frame_list = _mock.generate_frame_list

    cfg = MockConfig()
    frames = generate_frame_list(duration=30.0, cfg=cfg)
    print(f"Self-test: processing {len(frames)} multi-sensor frames...")

    pipeline = SignalPipeline()
    processed_count = 0
    for f in frames:
        result = pipeline.feed(f.timestamp, f.respiration_raw, f.ecg_raw,
                               f.eda_raw, f.acc_magnitude, f.temp_skin,
                               ecg_samples=getattr(f, "ecg_samples", None))
        if result is not None:
            processed_count += 1

    print(f"Warmup frames dropped: {len(frames) - processed_count}")
    print(f"Processed frames: {processed_count}")
    if processed_count > 0:
        print(f"Last: RR={pipeline._last_rr:.1f}  HR={pipeline._last_hr:.1f}  "
              f"RMSSD={pipeline._last_rmssd:.1f}  EDA_tonic={pipeline._last_eda_tonic:.2f}  "
              f"Motion={pipeline._last_motion:.4f}")
