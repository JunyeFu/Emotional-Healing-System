"""
SRP OSC Sender — JSON over OSC to TouchDesigner.

Sends the same v1.2 JSON frames via OSC to TD's OSC In DAT.
OSC avoids Windows UDP loopback firewall issues by using a different
transport path that TD natively supports.

Ports:
  TD: 5007 (OSC In DAT)
  Unity: 5008 (future)
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

OSC_TD_PORT = 5007
OSC_UNITY_PORT = 5008


class OSCSender:
    """Sends JSON frames over OSC to TouchDesigner."""

    def __init__(self, host: str = "127.0.0.1", port: int = OSC_TD_PORT):
        from pythonosc import udp_client
        self.host = host
        self.port = port
        self.client = udp_client.SimpleUDPClient(host, port)
        self.frame_count = 0
        self.error_count = 0

    def send(self, message: dict) -> bool:
        """Send a JSON message as an OSC string argument.

        The message dict is serialized to JSON and sent to /srp/frame.
        """
        try:
            payload = json.dumps(message, ensure_ascii=False)
            self.client.send_message("/srp/frame", payload)
            self.frame_count += 1
            return True
        except Exception as e:
            logger.warning(f"OSC send to {self.host}:{self.port} failed: {e}")
            self.error_count += 1
            return False

    def close(self):
        try:
            if hasattr(self.client, '_sock'):
                self.client._sock.close()
        except Exception:
            pass

    def stats(self) -> dict:
        return {
            "frames_sent": self.frame_count,
            "errors": self.error_count,
            "target": f"{self.host}:{self.port}",
        }


if __name__ == "__main__":
    import time
    sender = OSCSender()
    print(f"OSC Sender self-test → {sender.host}:{sender.port}")
    for i in range(5):
        test_msg = {
            "version": "1.2",
            "timestamp": time.time(),
            "scores": {"breath_sync": 72.5, "breath_depth": 58.1,
                       "hrv_coherence": 68.3, "eda_calm": 70.8},
            "calm_index": 67.4,
        }
        ok = sender.send(test_msg)
        print(f"  Frame {i + 1}: {'OK' if ok else 'FAIL'}")
        time.sleep(0.1)
    print(f"\nStats: {sender.stats()}")
    sender.close()
