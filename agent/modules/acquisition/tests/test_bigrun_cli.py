"""Offline integration only: generated waveforms never count as device acceptance."""
import csv
import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from bigrun.__main__ import main
from bigrun.recording import CandidateRecording, export_recording, inspect_recording


def write_csv(path, header, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def test_raw_export_retains_two_acc_samples_and_labels_nominal_time(tmp_path):
    recording = CandidateRecording(tmp_path, "SYNTHETIC-EXPORT", "mock", {})
    packet = bytes.fromhex("0f12061400eb0106ff8b00ee0108ff8ef8260127")
    recording.record(packet, 1_000_000_000)
    recording.record(packet, 1_080_000_000)
    recording.close("COMPLETED")
    report = export_recording(recording.path, tmp_path / "export", 125, 25)
    assert report["sample_counts"]["acc"] == 4
    data = np.genfromtxt(tmp_path / "export/acc.csv", delimiter=",", names=True)
    assert np.allclose(np.diff(data["time_s"]), .04)
    assert data["z"].tolist() == [-117, -114, -117, -114]
    assert "UNVERIFIED" in report["timing"]
    assert inspect_recording(recording.path)["streams"]["acc"]["host_rate_estimate_hz"] == 25


def test_resp_cli_calibration_then_separate_frozen_validation(tmp_path):
    fs = 25
    t = np.arange(fs * 150) / fs
    for name, phase in (("fit", 0), ("validation", .7)):
        x = np.column_stack([100 + np.sin(2 * np.pi * .1 * t + phase),
                             np.full(len(t), 300), np.full(len(t), -50)])
        ref = sosfilt(butter(2, [.04, .8], btype="bandpass", fs=fs, output="sos"), x[:, 0] - 100)
        write_csv(tmp_path / f"{name}-acc.csv", ["time_s", "x", "y", "z"], np.column_stack([t, x]))
        write_csv(tmp_path / f"{name}-ref.csv", ["time_s", "value"], zip(t, ref))
    profile = tmp_path / "profile.json"
    main(["calibrate-resp", "--acc", str(tmp_path / "fit-acc.csv"), "--reference",
          str(tmp_path / "fit-ref.csv"), "--acc-hz", "25", "--out", str(profile)])
    before = profile.read_bytes()
    report = tmp_path / "validation.json"
    main(["validate-resp", "--acc", str(tmp_path / "validation-acc.csv"), "--reference",
          str(tmp_path / "validation-ref.csv"), "--profile", str(profile), "--out", str(report)])
    assert profile.read_bytes() == before
    metrics = json.loads(report.read_text())
    assert metrics["waveform_correlation"] > .99
    assert metrics["automatic_acceptance"] is False
    with pytest.raises(ValueError, match="DIFFERENT_RECORDING"):
        main(["validate-resp", "--acc", str(tmp_path / "fit-acc.csv"), "--reference",
              str(tmp_path / "fit-ref.csv"), "--profile", str(profile), "--out", str(tmp_path / "invalid.json")])


def test_heart_cli_uses_neurokit_and_independent_reference_beats(tmp_path):
    fs = 125
    t = np.arange(30 * fs) / fs
    beats = np.arange(.8, 29., 1.)
    signal = sum(np.exp(-((t - b) / .015) ** 2) for b in beats)
    write_csv(tmp_path / "ecg.csv", ["time_s", "value"], zip(t, signal))
    write_csv(tmp_path / "reference.csv", ["time_s"], ((b,) for b in beats))
    main(["calibrate-heart", "--ecg", str(tmp_path / "ecg.csv"), "--reference-beats",
          str(tmp_path / "reference.csv"), "--polarity", "1", "--out", str(tmp_path / "heart.json")])
    result = json.loads((tmp_path / "heart.json").read_text())
    assert result["metrics"]["matched_beats"] >= 26
    assert result["real_device_acceptance"] == "NOT_RUN"
    original = (tmp_path / "heart.json").read_bytes()
    shifted = sum(np.exp(-((t - b - .02) / .015) ** 2) for b in beats)
    write_csv(tmp_path / "validation-ecg.csv", ["time_s", "value"], zip(t, shifted))
    write_csv(tmp_path / "validation-reference.csv", ["time_s"], ((b + .02,) for b in beats))
    main(["validate-heart", "--ecg", str(tmp_path / "validation-ecg.csv"), "--reference-beats",
          str(tmp_path / "validation-reference.csv"), "--profile", str(tmp_path / "heart.json"),
          "--out", str(tmp_path / "heart-validation.json")])
    assert (tmp_path / "heart.json").read_bytes() == original
    assert json.loads((tmp_path / "heart-validation.json").read_text())["metrics"]["matched_beats"] >= 26


def test_empty_and_gapped_inputs_do_not_generate_a_calibration(tmp_path):
    from bigrun.calibration import read_csv, sample_rate
    write_csv(tmp_path / "empty.csv", ["time_s", "value"], [])
    with pytest.raises(ValueError, match="FINITE_SAMPLES"):
        read_csv(tmp_path / "empty.csv", ["time_s", "value"])
    with pytest.raises(ValueError, match="GAPPED"):
        sample_rate(np.array([0., .04, .08, .2]))


def test_capture_entry_records_fake_ble_and_outputs_candidate_frames(tmp_path, monkeypatch):
    from bigrun import __main__ as cli
    from bigrun.driver import BigRunDriver
    from bigrun.recording import open_recording

    class Client:
        def __init__(self, *args, **kwargs):
            self.is_connected = False
            self.params = {0x60: 0, 0x62: 0, 0x61: 0}
        async def connect(self): self.is_connected = True
        async def disconnect(self): self.is_connected = False
        async def start_notify(self, uuid, callback): self.callback = callback
        async def stop_notify(self, uuid): pass
        async def write_gatt_char(self, uuid, data, **kwargs):
            if data[1] == 15 and data[2] in self.params:
                if data[3] == 1:
                    self.params[data[2]] = data[4]
                else:
                    self.callback(None, bytes([15, data[2], 0, self.params[data[2]]]) + bytes(16))
            if data[:3] == bytes([0xFC, 0x14, 4]):
                for raw in ("4160271127132710270726fd26f926fb2702270c",
                            "0f12061400eb0106ff8b00ee0108ff8ef8260127",
                            "14069d0e1cdd0000000000000000000000000000"):
                    self.callback(None, bytes.fromhex(raw))

    monkeypatch.setattr(cli, "BigRunDriver", lambda *a, **kw: BigRunDriver(*a, **kw, client_factory=Client))
    monkeypatch.setattr(cli, "CandidateRecording",
                        lambda root, session_id, policy, settings: CandidateRecording(root, session_id, "mock", settings))
    output = tmp_path / "frames.jsonl"
    main(["capture", "--address", "fake", "--root", str(tmp_path), "--mode", "ecg",
          "--seconds", ".01", "--ecg-hz", "125", "--acc-hz", "25", "--frames", str(output)])
    frame = json.loads(output.read_text().splitlines()[0])
    assert len(frame["raw_frame"]["ecg_samples"]) == 9
    assert frame["heart_rate_bpm"] == 73.89
    assert frame["breath_phase"] == "unknown"
    assert frame["connection_phase"] == "receiving"
    archive = next((tmp_path / "sessions").iterdir())
    reader = open_recording(archive)
    assert reader.envelope["manifest"]["source_policy"] == "mock"
    assert reader.verify().valid


def test_documentation_local_links_excluding_fenced_command_examples():
    agent = ROOT.parents[1]
    docs = [ROOT / "bigrun/README.md", ROOT / "README.md", agent / "runtime/README.md"]
    docs += [agent / "modules/touchdesigner/t01_telemetry_panel/README.md",
             agent / "modules/touchdesigner/t01_telemetry_panel/design/bigrun-workbench.md",
             agent / "work/2026-10-19_bigrun-td-update.md",
             agent / "work/2026-10-20_ectri-ble-integration.md"]
    checked = 0
    for doc in docs:
        # PowerShell [double](Read-Host ...) inside code fences is not a Markdown link.
        prose = re.sub(r"```[^\n]*\n.*?```", "", doc.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"\]\((?!https?://|#)([^)]+)\)", prose):
            assert (doc.parent / target.split("#")[0]).exists(), (doc, target)
            checked += 1
    assert checked >= 20
