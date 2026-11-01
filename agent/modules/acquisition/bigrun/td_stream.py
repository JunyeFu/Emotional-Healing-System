"""Development-only local TD stream. Never emits session/control receipts."""
import json
import socket
import time

from .recording import SCOPE


class TDPublisher:
    def __init__(self, recording, ecg_hz, acc_hz):
        if recording.source_policy != "real":
            raise ValueError("TD_BIGRUN_REQUIRES_REAL_SOURCE")
        self.recording = recording
        self.rates = {"ecg": ecg_hz, "acc": acc_hz}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sequence = 0

    def send(self, **payload):
        self.sequence += 1
        message = dict(message_type="bigrun_preview", version="1.0", source_mode="real",
                       device="BigRun Team", evidence_scope=SCOPE, formal_capable=False,
                       stream_id=self.recording.session_id, packet_seq=self.sequence,
                       sent_monotonic_ns=time.monotonic_ns(), **payload)
        self.socket.sendto(json.dumps(message, allow_nan=False).encode("utf-8"), ("127.0.0.1", 5005))

    def packet(self, packet, received_ns, driver, proxy):
        self.send(kind=packet.kind, received_monotonic_ns=received_ns,
                  samples=packet.samples, metadata=packet.metadata,
                  sample_rate_hz_nominal=self.rates.get(packet.kind),
                  respiration_proxy=list(map(float, proxy)) if proxy is not None else [],
                  resp_warmed_up=bool(driver.resp_estimator and driver.resp_estimator.warmed_up))

    def status(self, driver, snapshot, error=None):
        self.send(kind="status", received_monotonic_ns=time.monotonic_ns(), samples=[],
                  connected=driver.is_connected, archive=str(self.recording.path),
                  ecg_hz_nominal=self.rates["ecg"], acc_hz_nominal=self.rates["acc"],
                  resp_profile_loaded=driver.resp_estimator is not None,
                  **snapshot, error=error)

    def close(self):
        self.socket.close()
