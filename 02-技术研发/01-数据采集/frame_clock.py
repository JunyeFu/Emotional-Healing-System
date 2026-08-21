"""SRP frame clock.

The clock emits 10 Hz coordination frames while preserving every native ECG
sample and timestamp collected since the previous tick. Feature extraction
must consume ``ecg_samples``; ``ecg_raw`` is display-only and is never an
averaged substitute for the native stream.
"""

import time
import threading
import queue
import logging
from dataclasses import dataclass, field
from typing import Optional

from ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


@dataclass
class RawFrame:
    """Multi-sensor raw data frame — unified shape for mock and real sources.

    Mirrors mock_data.MockFrame for pipeline compatibility. Missing channels
    are explicit ``None`` values and cannot masquerade as neutral readings.
    """
    timestamp: float

    # Respiration (PLUX belt >=25Hz → 10Hz downsample)
    respiration_raw: Optional[float] = None

    # ECG display snapshot plus the authoritative native-rate batch.
    ecg_raw: Optional[float] = None
    ecg_samples: tuple[tuple[float, float], ...] = ()

    # EDA (wristband >=4Hz → latest)
    eda_raw: Optional[float] = None

    # Acceleration (device IMU)
    acc_magnitude: Optional[float] = None

    # Skin temperature (EDA wristband thermistor)
    temp_skin: Optional[float] = None

    # Breath metadata (filled by pipeline, default here for compat)
    breath_phase: str = "exhale"
    respiration_depth: float = 0.5

    # Session metadata
    weather_type: str = "storm"
    guidance_prompt: str = ""
    signal_validity: dict[str, bool] = field(default_factory=dict)


class FrameClock(threading.Thread):
    """Reads sensor ring buffers at 10 Hz, assembles RawFrames into a queue.

    Runs in its own daemon thread. The main thread consumes from
    output_queue with blocking get() at 100ms pacing.
    """

    def __init__(
        self,
        ecg_buf: Optional[RingBuffer] = None,
        resp_buf: Optional[RingBuffer] = None,
        eda_buf: Optional[RingBuffer] = None,
        acc_buf: Optional[RingBuffer] = None,
        temp_buf: Optional[RingBuffer] = None,
        rate_hz: float = 10.0,
        queue_size: int = 100,
    ):
        super().__init__(daemon=True, name="FrameClock")
        self.ecg_buf = ecg_buf
        self.resp_buf = resp_buf
        self.eda_buf = eda_buf
        self.acc_buf = acc_buf
        self.temp_buf = temp_buf

        self.rate_hz = rate_hz
        self.interval = 1.0 / rate_hz
        self.output_queue: queue.Queue[RawFrame] = queue.Queue(maxsize=queue_size)
        self._stop = threading.Event()
        self.frame_id = 0
        self._last_ecg_timestamp = float("-inf")

        # Device connection flags (set by DeviceManager after connect)
        self.ecg_connected = False
        self.resp_connected = False
        self.eda_connected = False
        self.acc_connected = False
        self.temp_connected = False

    def run(self):
        logger.info(f"FrameClock started @ {self.rate_hz} Hz")
        while not self._stop.is_set():
            ts = time.time()
            frame = self._assemble(ts)

            try:
                self.output_queue.put(frame, timeout=0.5)
                self.frame_id += 1
            except queue.Full:
                logger.warning("FrameClock output queue full, dropping frame")

            elapsed = time.time() - ts
            sleep_time = max(0, self.interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("FrameClock stopped")

    def _assemble(self, ts: float) -> RawFrame:
        """Read latest from each buffer, downsample where needed."""

        # ECG: preserve every newly acquired native-rate sample. The latest
        # value is exposed only for display/logging compatibility.
        if self.ecg_connected and self.ecg_buf and not self.ecg_buf.is_empty:
            ecg_samples = self.ecg_buf.read_after(self._last_ecg_timestamp)
            if ecg_samples:
                self._last_ecg_timestamp = ecg_samples[-1][0]
                ecg_val = ecg_samples[-1][1]
            else:
                ecg_val = None
        else:
            ecg_samples = []
            ecg_val = None

        # Respiration: downsample ≥25→10Hz (approx 3 samples)
        if self.resp_connected and self.resp_buf and not self.resp_buf.is_empty:
            resp_window = self.resp_buf.read_window(3)
            resp_val = sum(resp_window) / len(resp_window) if resp_window else None
        else:
            resp_val = None

        # EDA: use latest (4 Hz → hold last value)
        if self.eda_connected and self.eda_buf and not self.eda_buf.is_empty:
            eda_val = self.eda_buf.read_latest()
        else:
            eda_val = None

        # ACC: use latest
        if self.acc_connected and self.acc_buf and not self.acc_buf.is_empty:
            acc_val = self.acc_buf.read_latest()
        else:
            acc_val = None

        # Temp: use latest
        if self.temp_connected and self.temp_buf and not self.temp_buf.is_empty:
            temp_val = self.temp_buf.read_latest()
        else:
            temp_val = None

        return RawFrame(
            timestamp=ts,
            respiration_raw=resp_val,
            ecg_raw=ecg_val,
            ecg_samples=tuple(ecg_samples),
            eda_raw=eda_val,
            acc_magnitude=acc_val,
            temp_skin=temp_val,
            signal_validity={
                "resp": resp_val is not None,
                "ecg": bool(ecg_samples),
                "eda": eda_val is not None,
                "acc": acc_val is not None,
                "temp": temp_val is not None,
            },
        )

    def stop(self):
        self._stop.set()

    @property
    def queue_backlog(self) -> int:
        return self.output_queue.qsize()
