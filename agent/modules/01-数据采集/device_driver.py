"""
SRP Device Driver — abstract interface for BLE biosignal devices.

Each concrete driver (Polar H10, PLUX belt, EDA wristband) implements
this ABC. Drivers run in a shared asyncio event loop managed by DeviceManager.
"""

from abc import ABC, abstractmethod


class DeviceDriver(ABC):
    """Abstract BLE device driver.

    Each driver manages one physical sensor, pushing samples into a
    RingBuffer at its native sampling rate.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Scan, discover, and connect to the device. Return True on success."""

    @abstractmethod
    async def start_streaming(self) -> None:
        """Enable notifications / start data streaming from the device."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop streaming and disconnect cleanly."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if device is actively connected."""

    @property
    @abstractmethod
    def device_name(self) -> str:
        """Human-readable device identifier for logging / UI."""
