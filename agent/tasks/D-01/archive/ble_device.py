"""
SRP BLE Device Interface (Sprint 1 — Architecture Skeleton)
=============================================================
Abstract interface for biosignal data sources. Polar H10 will be the first
concrete implementation (Sprint 2/3).

Defines:
  1. BioFrame        — unified data frame (same shape as MockFrame)
  2. BioDataSource    — ABC for any signal source
  3. PolarH10Config   — connection parameters for Polar H10
  4. PolarH10Source   — skeleton with detailed implementation plan
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional
from dataclasses import dataclass, field


# ── Unified Data Frame ──────────────────────────────────────────────────────

@dataclass
class BioFrame:
    """A single frame of biosignal data (mirrors MockFrame for pipeline compat)."""
    timestamp: float
    respiration_raw: float
    ecg_raw: float
    breath_phase: str = ""
    guidance_prompt: str = ""
    weather_type: str = "storm"
    weather_intensity_base: float = 0.5

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "respiration_raw": round(self.respiration_raw, 4),
            "ecg_raw": round(self.ecg_raw, 4),
            "breath_phase": self.breath_phase,
            "guidance_prompt": self.guidance_prompt,
            "weather_type": self.weather_type,
            "weather_intensity_base": round(self.weather_intensity_base, 4),
        }


# ── Abstract Data Source ────────────────────────────────────────────────────

class BioDataSource(ABC):
    """Abstract interface for any biosignal data source (mock or real).

    This allows main.py to accept any source via dependency injection,
    making the pipeline agnostic to data origin.
    """

    @abstractmethod
    def start(self) -> None:
        """Initialize and begin data acquisition."""

    @abstractmethod
    def read_frame(self) -> Optional[BioFrame]:
        """Read the next available data frame (blocking or None if no data)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop data acquisition and clean up resources."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if device is actively streaming."""


# ── Polar H10 Configuration ─────────────────────────────────────────────────

@dataclass
class PolarH10Config:
    """Polar H10 BLE connection parameters."""
    device_address: str = ""  # BLE MAC (e.g. "XX:XX:XX:XX:XX:XX"), empty = auto-detect by name
    device_name: str = "Polar H10"
    # Standard BLE UUIDs for Polar H10
    ecg_service_uuid: str = "0000180d-0000-1000-8000-00805f9b34fb"
    ecg_char_uuid: str = "00002a37-0000-1000-8000-00805f9b34fb"
    ecg_sampling_rate: int = 130  # H10 native ECG rate (Hz)
    # Pipeline output rate
    target_frame_rate: int = 10   # Down-sampled to 10Hz for the pipeline


# ── Polar H10 Source (Skeleton) ─────────────────────────────────────────────

class PolarH10Source(BioDataSource):
    """Polar H10 BLE ECG data source with ECG-derived respiration.

    IMPLEMENTATION PLAN (Sprint 2/3)
    --------------------------------
    1. CONNECTION: Use bleak (async BLE, already in requirements.txt) to connect
       to Polar H10 by device_name filter or MAC address. Requires Bluetooth
       adapter + prior pairing (Windows: Settings → Bluetooth → pair H10).

    2. ECG STREAMING: Subscribe to ECG characteristic (UUID 00002a37-...).
       H10 streams ECG at 130 Hz as int16 samples. Accumulate in a ring buffer.

    3. RESPIRATION DERIVATION: Polar H10 does NOT natively measure respiration.
       Two options:
         a. EDR (ECG-Derived Respiration): Use NeuroKit2's ecg_rsp() to extract
            respiratory waveform from R-wave amplitude modulation.
         b. Separate respiratory belt sensor (e.g., via Arduino serial / BLE).
       Default approach: EDR as primary, belt as optional upgrade.

    4. DOWN-SAMPLING: Collect 130 Hz ECG → buffer 1 second → generate one
       BioFrame at 10 Hz with down-sampled features.

    5. ASYNC BRIDGE: bleak is asyncio-based; current pipeline is synchronous.
       Solution: background asyncio thread + queue.Queue for producer/consumer.
       ```
       asyncio.run() in daemon thread → push BioFrames to queue.Queue
       main loop → queue.get() for each pipeline tick (100ms)
       ```

    6. BREATH PHASE: Classified downstream by signal_pipeline.py from the
       derived respiration waveform (same as mock data path).

    7. RECONNECTION: Handle BLE disconnection gracefully. Auto-reconnect with
       exponential backoff (1s, 2s, 4s, max 15s). Notify pipeline of gaps
       via BioFrame.metadata flags.

    KNOWN LIMITATIONS
    -----------------
    - bleak requires Python 3.10+ on Windows with Bluetooth LE adapter.
    - ECG-Derived Respiration is less accurate than a physical respiratory belt.
    - No respiratory belt hardware selected yet; belt would require separate
      BLE/Serial driver.
    - asyncio bridge adds ~1-2ms latency per frame (acceptable at 10Hz).

    REFERENCES
    ----------
    - Polar H10: https://www.polar.com/en/sensors/h10-heart-rate-sensor
    - bleak docs: https://bleak.readthedocs.io/en/stable/
    - NeuroKit2 ecg_rsp(): https://neuropsychology.github.io/NeuroKit/
    - Polar BLE spec: "Polar H10 Heart Rate Monitor — BLE Communication Notes"
    """

    def __init__(self, config: PolarH10Config | None = None):
        self.config = config or PolarH10Config()
        self._connected = False

    def start(self) -> None:
        raise NotImplementedError(
            "PolarH10Source requires BLE hardware. "
            "See docstring for Sprint 2/3 implementation plan."
        )

    def read_frame(self) -> Optional[BioFrame]:
        raise NotImplementedError(
            "PolarH10Source requires BLE hardware. "
            "See docstring for Sprint 2/3 implementation plan."
        )

    def stop(self) -> None:
        raise NotImplementedError(
            "PolarH10Source requires BLE hardware. "
            "See docstring for Sprint 2/3 implementation plan."
        )

    def is_connected(self) -> bool:
        return self._connected


# ── Mock Data Source Wrapper ─────────────────────────────────────────────────

class MockDataSource(BioDataSource):
    """Adapter wrapping mock_data module behind BioDataSource interface.

    Useful for testing the data source abstraction without hardware.
    """

    def __init__(self, weather_type: str = "storm", duration: float = 60.0):
        import importlib
        import os, sys
        _root = os.path.dirname(os.path.abspath(__file__))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        self._mock = importlib.import_module("mock_data")
        self._cfg = self._mock.MockConfig.for_weather(weather_type)
        self._generator: Optional[Generator] = None
        self._duration = duration

    def start(self) -> None:
        self._generator = self._mock.generate_frames(duration=self._duration, cfg=self._cfg)

    def read_frame(self) -> Optional[BioFrame]:
        if self._generator is None:
            return None
        try:
            mock_frame = next(self._generator)
            return BioFrame(
                timestamp=mock_frame.timestamp,
                respiration_raw=mock_frame.respiration_raw,
                ecg_raw=mock_frame.ecg_raw,
                breath_phase=mock_frame.breath_phase,
                guidance_prompt=mock_frame.guidance_prompt,
                weather_type=mock_frame.weather_type,
                weather_intensity_base=mock_frame.weather_intensity_base,
            )
        except StopIteration:
            return None

    def stop(self) -> None:
        self._generator = None

    def is_connected(self) -> bool:
        return self._generator is not None
