from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GATE = (
    ROOT
    / "02-技术研发"
    / "04-Unity视觉"
    / "SRP-Weather-Visual"
    / "Assets"
    / "Scripts"
    / "Editor"
    / "FormalBuildGate.cs"
)


def test_unity_formal_build_invokes_current_g02_asset_gate_fail_closed() -> None:
    source = GATE.read_text(encoding="utf-8")

    assert "ValidateAssetGovernance();" in source
    assert '"scan-assets"' in source
    assert "UseShellExecute = false" in source
    assert "ASSET_LICENSE_GATE_BLOCKED" in source
    assert "ASSET_LICENSE_GATE_UNAVAILABLE" in source
    assert "WaitForExit(120000)" in source
