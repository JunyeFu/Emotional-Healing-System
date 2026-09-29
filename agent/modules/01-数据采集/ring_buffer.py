"""
SRP Ring Buffer — thread-safe circular buffer for sensor samples.

Each device pushes samples at its native rate into a RingBuffer. Consumers may
read timestamped batches without destroying native timing information.
"""

import threading
from collections import deque


class RingBuffer:
    """Thread-safe ring buffer for sensor samples with timestamp."""

    def __init__(self, capacity: int):
        self._buf: deque[tuple[float, float]] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, timestamp: float, value: float) -> None:
        with self._lock:
            self._buf.append((timestamp, value))

    def read_latest(self) -> float | None:
        """Return most recent value, or ``None`` if no sample exists."""
        with self._lock:
            if self._buf:
                return self._buf[-1][1]
            return None

    def read_latest_ts(self) -> tuple[float, float] | None:
        """Return the most recent timestamped sample, or ``None``."""
        with self._lock:
            if self._buf:
                return self._buf[-1]
            return None

    def read_window(self, n: int) -> list[float]:
        """Return last n values for downsampling."""
        with self._lock:
            return [v for _, v in list(self._buf)[-n:]]

    def read_after(self, timestamp: float) -> list[tuple[float, float]]:
        """Return samples newer than ``timestamp`` in acquisition order.

        The read is non-destructive. A consumer keeps its own cursor so other
        consumers can independently preserve the same native-rate stream.
        """
        with self._lock:
            return [(ts, value) for ts, value in self._buf if ts > timestamp]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._buf)

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._buf) == 0
