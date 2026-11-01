"""Start mock ingress only; TD preparation/start/pause/end remain operator actions."""
import argparse
import json
from pathlib import Path
import socket
import time

from manual_mock_service import ManualMockBridge
from study_simulation import make

ROOT = Path(__file__).resolve().parents[4]


def serve(speed=1):
    dataset = ROOT / 'agent/local/artifacts/physiology-study-20261008/A'
    if not (dataset / 'raw.npz').exists():
        print('Generating synthetic mock inputs.', flush=True)
        make(dataset, 'A', 20261008)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as output:
        control.bind(('127.0.0.1', 5007))
        control.settimeout(.02)
        def send(payload):
            output.sendto(json.dumps(payload, ensure_ascii=True, allow_nan=False).encode('ascii'), ('127.0.0.1', 5005))
        bridge = ManualMockBridge(ROOT / 'agent/local/artifacts/td-manual-workbench/p02', dataset, send, speed)
        print('MOCK_READY: TD UDP 5005, operator status UDP 5007; waiting for your Start action. Ctrl+C stops ingress.', flush=True)
        due = time.monotonic()
        try:
            while True:
                try:
                    raw, peer = control.recvfrom(65536)
                except socket.timeout:
                    raw = None
                if raw is not None:
                    bridge.on_status(json.loads(raw))
                now = time.monotonic()
                if now >= due:
                    bridge.tick()
                    due = now + .1 / speed
        finally:
            bridge.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--speed', type=float, default=1)
    args = parser.parse_args()
    if not 0 < args.speed <= 10:
        parser.error('speed must be in (0, 10]')
    try:
        serve(args.speed)
    except KeyboardInterrupt:
        print('MOCK_STOPPED', flush=True)
