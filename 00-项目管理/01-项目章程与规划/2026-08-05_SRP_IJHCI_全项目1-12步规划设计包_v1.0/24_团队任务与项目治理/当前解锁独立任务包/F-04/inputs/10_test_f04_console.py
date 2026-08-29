from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from f04_console import (  # noqa: E402
    FIXTURE_SCHEMA_VERSION,
    FORMAL_TELEMETRY_FIELDS,
    PAGE_DEFINITIONS,
    SCENARIO_IDS,
    ConsoleSnapshot,
    FixtureValidationError,
    StaticFixtureAdapter,
    load_and_validate_fixture,
    validate_fixture,
)
from f04_node_plan import build_node_plan, write_host_artifacts  # noqa: E402


FIXTURE = ROOT / "fixtures" / "f04-static-display-fixture-v1.json"


def fixture_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_reuses_all_29_v21_fields_and_four_weather_ids():
    validated = load_and_validate_fixture(FIXTURE)
    assert validated["fixture_schema_version"] == FIXTURE_SCHEMA_VERSION
    assert len(FORMAL_TELEMETRY_FIELDS) == 29
    assert {item["telemetry"]["module_id"] for item in validated["scenarios"]} == {
        "storm", "heat", "snow", "fade"
    }
    for scenario in validated["scenarios"]:
        assert set(scenario["telemetry"]) == FORMAL_TELEMETRY_FIELDS


def test_fixture_covers_quality_states_and_out_of_order_replay():
    payload = fixture_payload()
    assert [item["telemetry"]["fallback_state"] for item in payload["scenarios"]] == [
        "GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED", "GOOD"
    ]
    assert payload["scenarios"][-1]["replay_order"] < payload["scenarios"][-2]["replay_order"]
    assert payload["scenarios"][-1]["telemetry"]["frame_seq"] < payload["scenarios"][-2]["telemetry"]["frame_seq"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item["telemetry"].pop("clock_domain_id"),
        lambda item: item["telemetry"].update(schema_version="9.9"),
        lambda item: item["telemetry"].update(calm_index=0.5),
        lambda item: item["telemetry"].update(module_id="rain"),
        lambda item: item["telemetry"].update(clock_drift_ppm=math.nan),
    ],
)
def test_invalid_or_nonfinite_telemetry_fails_closed(mutation):
    payload = fixture_payload()
    mutation(payload["scenarios"][0])
    with pytest.raises(FixtureValidationError):
        validate_fixture(payload)


def test_forward_compatible_telemetry_field_is_filtered_not_displayed():
    payload = fixture_payload()
    payload["scenarios"][0]["telemetry"]["future_display_hint"] = "ignore-me"
    validated = validate_fixture(payload)
    assert set(validated["scenarios"][0]["telemetry"]) == FORMAL_TELEMETRY_FIELDS


def test_display_only_is_not_accepted_inside_formal_telemetry():
    payload = fixture_payload()
    payload["scenarios"][0]["telemetry"]["display_only"] = deepcopy(
        payload["scenarios"][0]["display_only"]
    )
    validated = validate_fixture(payload)
    assert "display_only" not in validated["scenarios"][0]["telemetry"]


def test_ten_pages_have_complete_unique_field_mappings_and_readonly_banner():
    assert len(PAGE_DEFINITIONS) == 10
    assert len({page["id"] for page in PAGE_DEFINITIONS}) == 10
    all_paths = {
        path
        for page in PAGE_DEFINITIONS
        for path in page["field_paths"]
    }
    required = {
        "telemetry.session_id",
        "telemetry.resp_device_state",
        "display_only.respiration.raw_25hz",
        "telemetry.signal_quality.ecg",
        "telemetry.target_phase",
        "display_only.cycle_summary.cycle_id",
        "telemetry.clock_drift_ppm",
        "telemetry.fallback_state",
        "display_only.log_status.write_state",
        "display_only.request_placeholders.abort.status",
    }
    assert required <= all_paths
    assert all(page["banner"] == "READ ONLY / DEV-REPLAY / NOT LIVE" for page in PAGE_DEFINITIONS)


def test_static_fixture_adapter_reads_five_immutable_console_snapshots():
    adapter = StaticFixtureAdapter(FIXTURE)
    assert adapter.scenario_ids == SCENARIO_IDS == (
        "good_storm",
        "degraded_heat",
        "unusable_snow",
        "disconnected_fade",
        "out_of_order_storm",
    )
    for scenario_id in SCENARIO_IDS:
        adapter.scenario_id = scenario_id
        snapshot = adapter.read_snapshot()
        assert isinstance(snapshot, ConsoleSnapshot)
        assert snapshot.meta["scenario_id"] == scenario_id
        assert snapshot.meta["replay_state"] == "DEV-REPLAY"
        assert set(snapshot.telemetry) == FORMAL_TELEMETRY_FIELDS
        with pytest.raises(TypeError):
            snapshot.telemetry["frame_seq"] = 999


def test_all_fifty_page_scenario_combinations_resolve_through_snapshot_interface():
    adapter = StaticFixtureAdapter(FIXTURE)
    observed = set()
    for scenario_id in SCENARIO_IDS:
        adapter.scenario_id = scenario_id
        for page in PAGE_DEFINITIONS:
            adapter.page_id = page["id"]
            snapshot = adapter.read_snapshot()
            values = [snapshot.resolve(path) for path in page["field_paths"]]
            assert snapshot.meta["page_id"] == page["id"]
            assert len(values) == len(page["field_paths"])
            observed.add((page["id"], scenario_id))
    assert len(observed) == 50


def test_static_adapter_can_be_replaced_without_page_specific_input_contract():
    class ReplacementSource:
        def read_snapshot(self):
            return StaticFixtureAdapter(FIXTURE).read_snapshot()

    source = ReplacementSource()
    snapshot = source.read_snapshot()
    for page in PAGE_DEFINITIONS:
        assert [snapshot.resolve(path) for path in page["field_paths"]]


def test_fixture_declares_disabled_runtime_and_request_permissions():
    payload = load_and_validate_fixture(FIXTURE)
    permissions = payload["permissions"]
    assert permissions["udp_5005"]["active"] is False
    assert permissions["udp_5005"]["label"] == "T-01 NOT ACTIVE"
    assert permissions["manual_mark"]["enabled"] is False
    assert permissions["abort"]["enabled"] is False
    assert permissions["manual_mark"]["label"] == "T-02 NOT ACTIVE"
    assert permissions["abort"]["label"] == "T-02 NOT ACTIVE"
    assert permissions["network_outputs"] == []
    assert permissions["spout_outputs"] == []


def test_source_tree_contains_no_forbidden_capability_tokens():
    forbidden = ("9054", "spoutout", "udpout", "tcpip", "random.", "threshold_editor")
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore").lower()
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".py", ".json", ".md"}
        and path.name != Path(__file__).name
    )
    assert not [token for token in forbidden if token in source_text]


def test_node_plan_is_scoped_idempotent_and_contains_ten_page_views():
    plan = build_node_plan()
    assert plan["replace_scope"] == "/project1/F04_ReadonlyConsole"
    assert plan["replacement_policy"] == "replace_exact_root_only"
    page_nodes = [node for node in plan["nodes"] if node["role"] == "page_view"]
    assert len(page_nodes) == 10
    assert {node["page_id"] for node in page_nodes} == {
        page["id"] for page in PAGE_DEFINITIONS
    }
    assert all(node["operator_type"] != "textTOP" for node in page_nodes)
    assert all(node["visual_mechanism"] != "text_dump" for node in page_nodes)
    page_navigation = [node for node in plan["nodes"] if node["role"] == "page_navigation"]
    scenario_navigation = [node for node in plan["nodes"] if node["role"] == "scenario_navigation"]
    assert len(page_navigation) == 10
    assert len(scenario_navigation) == 5
    assert {node["scenario_id"] for node in scenario_navigation} == set(SCENARIO_IDS)
    waveform_roles = {
        node["role"] for node in plan["nodes"]
        if node["path"].startswith("/project1/F04_ReadonlyConsole/SharedViews/WaveformPanel")
    }
    assert {"waveform_table", "waveform_dat_to_chop", "waveform_select", "waveform_math", "waveform_view"} <= waveform_roles
    udp = next(node for node in plan["nodes"] if node["role"] == "udp_placeholder")
    assert udp["port"] == 5005
    assert udp["active"] is False
    assert udp["label"] == "T-01 NOT ACTIVE"
    assert not [node for node in plan["nodes"] if node["permission"] == "network_output"]


def test_host_artifacts_are_deterministic_and_include_permissions_and_hashes(tmp_path):
    first = write_host_artifacts(tmp_path / "first", FIXTURE)
    second = write_host_artifacts(tmp_path / "second", FIXTURE)
    assert first["artifact_hashes"] == second["artifact_hashes"]
    assert first["fixture_sha256"] == second["fixture_sha256"]
    assert first["page_count"] == 10
    assert first["page_scenario_combinations"] == 50
    assert first["touchdesigner_required_build"] == "2025.32820"
    expected = {
        "page_manifest.json",
        "node_plan.json",
        "node_permissions.json",
        "host_build_manifest.json",
    }
    assert expected <= {path.name for path in (tmp_path / "first").iterdir()}


def test_touchdesigner_builder_has_exact_root_guard_and_runtime_evidence_steps():
    source = (ROOT / "build_f04_touchdesigner.py").read_text(encoding="utf-8")
    assert "op('/project1/F04_ReadonlyConsole')" in source
    assert "existing.destroy()" in source
    assert "udp.par.active = False" in source
    assert "project.save(" in source
    assert ".save(str(TOX_PATH))" in source
    assert "errors(recurse=True)" in source
    assert "scriptErrors(recurse=True)" in source
    assert "node.save(" in source
    assert "node.numpyArray()" in source
    assert "delayFrames=5" in source
    assert "buttonCOMP" in source
    assert "dattoCHOP" in source
    assert "selectCHOP" in source
    assert "mathCHOP" in source
    assert "opviewerTOP" in source
