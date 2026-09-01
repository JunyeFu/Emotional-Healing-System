from __future__ import annotations

import json

import pytest

from srp_session_core import SessionCoreError, load_breath_protocol_config


EXPECTED = {
    "storm": (
        ("inhale_1", "inhale", 3.0),
        ("hold_1", "hold", 3.0),
        ("exhale_1", "exhale", 3.0),
        ("hold_2", "hold", 3.0),
    ),
    "heat": (
        ("inhale_1", "inhale", 4.0),
        ("exhale_1", "exhale", 6.0),
    ),
    "snow": (
        ("inhale_1", "inhale", 5.0),
        ("exhale_1", "exhale", 5.0),
    ),
    "fade": (
        ("inhale_1", "inhale", 2.5),
        ("inhale_2", "inhale", 1.5),
        ("exhale_1", "exhale", 6.0),
    ),
}


def test_frozen_breath_protocol_has_exact_step_identity_and_timing() -> None:
    config = load_breath_protocol_config()
    assert config.breath_protocol_config_version == "2.2"
    assert set(config.modules) == set(EXPECTED)
    assert config.config_hash.startswith("sha256:")
    assert len(config.config_hash) == 71
    for module_id, expected in EXPECTED.items():
        actual = tuple(
            (step.step_id, step.phase, step.duration_seconds)
            for step in config.modules[module_id].steps
        )
        assert actual == expected


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["modules"]["storm"]["steps"].append(
            {"step_id": "hold_1", "phase": "hold", "duration_seconds": 3}
        ),
        lambda payload: payload["modules"]["fade"]["steps"][0].update(phase="hold"),
        lambda payload: payload["modules"]["heat"]["steps"][0].update(duration_seconds=0),
        lambda payload: payload["modules"].update(extra={"steps": []}),
    ],
)
def test_breath_protocol_drift_fails_closed(tmp_path, mutation) -> None:
    source = load_breath_protocol_config().source_payload
    mutation(source)
    path = tmp_path / "breath.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(SessionCoreError) as error:
        load_breath_protocol_config(path)
    assert error.value.code == "BREATH_PROTOCOL_CONFIG_INVALID"
