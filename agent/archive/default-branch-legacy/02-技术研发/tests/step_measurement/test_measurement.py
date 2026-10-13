from copy import deepcopy
from pathlib import Path
import json

import pytest

from srp_step_measurement.measurement import PHASES, STEPS, make_material, score_response

ROOT = Path(__file__).resolve().parents[2]


def frame():
    path = ROOT / "05-通信协议/contracts/consumer-fixtures/v2.2/unity/phase-instance-stream.jsonl"
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def evidence(**updates):
    value = dict(event_id="fixture-001", source_kind="SYNTHETIC_FIXTURE",
                 actual_source_ref="fixture:independent-actual",
                 actual_unknown_reason=None, clip_duration_ns=4_000_000_000,
                 cumulative_band="mid", cumulative_annotation_ref="fixture:band",
                 previous_recovery_value=0.25)
    value.update(updates)
    return value


def test_hold_identity_error_survives_coarse_phase_agreement():
    f = frame()
    f.update(target_step_id="hold_2", actual_step_id="hold_1", actual_phase="hold")
    result = make_material(f, evidence())
    assert result["truth"]["relation"] == "DIFFERENT_STEP"
    assert result["truth"]["actual"] == {"cycle_index": 0, "step_id": "hold_1"}


def test_actual_null_never_copies_target():
    f = frame()
    f.update(actual_step_id=None, actual_cycle_index=None, actual_phase="none", actual_progress=0)
    r = make_material(f, evidence(actual_source_ref=None, actual_unknown_reason="NO_OBSERVATION"))
    assert r["truth"]["actual"] is None
    assert r["truth"]["relation"] == "UNKNOWN"
    assert r["answer_key"]["C-A1"]["value"] == "UNKNOWN"


def test_unknown_requires_reason():
    f = frame()
    f.update(actual_step_id=None, actual_cycle_index=None, actual_phase="none", actual_progress=0)
    with pytest.raises(ValueError, match="ACTUAL_UNKNOWN_REASON_REQUIRED"):
        make_material(f, evidence(actual_source_ref=None))


def test_cycle_boundary_and_same_step_different_cycle():
    f = frame()
    f.update(target_step_id="hold_2", actual_step_id="hold_2", actual_phase="hold", actual_cycle_index=1)
    r = make_material(f, evidence())
    assert r["truth"]["next_target"] == {"cycle_index": 1, "step_id": "inhale_1"}
    assert r["truth"]["relation"] == "DIFFERENT_CYCLE"


def test_fade_second_inhale_and_next_step():
    f = frame()
    f.update(module_id="fade", target_phase="inhale", target_step_id="inhale_2",
             actual_phase="inhale", actual_step_id="inhale_1")
    r = make_material(f, evidence())
    assert r["truth"]["relation"] == "DIFFERENT_STEP"
    assert r["truth"]["next_target"]["step_id"] == "exhale_1"


def test_condition_equivalence_and_balanced_positions():
    f = frame()
    a = make_material(f, evidence(), seed=9)
    f["cue_mode"] = "abstract_pacer"
    b = make_material(f, evidence(), seed=9)
    assert a["items"] == b["items"]
    assert a["answer_key"] == b["answer_key"]
    for item in a["items"]:
        assert 0 <= a["answer_key"][item["item_id"]]["option_index"] < len(item["options"])
    assert a["source_frame_sha256"] != b["source_frame_sha256"]


def test_nonresponses_preserved_without_score_imputation():
    r = make_material(frame(), evidence())
    for status in ("SKIPPED", "TIMEOUT", "TECH_UNPRESENTED"):
        assert score_response(r, "C-A1", status, None)["correct"] is None
    key = r["answer_key"]["C-A1"]["option_index"]
    assert score_response(r, "C-A1", "RESPONDED", key)["correct"] == 1
    with pytest.raises(ValueError):
        score_response(r, "C-A1", "TECH_UNPRESENTED", key)


def test_input_is_not_mutated_and_cumulative_stays_independent():
    f = frame()
    before = deepcopy(f)
    r = make_material(f, evidence(previous_recovery_value=0.27))
    assert f == before
    assert r["truth"]["relation"] == "DIFFERENT_STEP"
    assert r["answer_key"]["C-C2"]["value"] == "INCREASED"


def test_old_contract_rejected():
    f = frame()
    f["schema_version"] = "2.1"
    with pytest.raises(ValueError, match="STEP_INSTANCE_REQUIRES_V22"):
        make_material(f, evidence())


@pytest.mark.parametrize("module,step", [(m, s) for m, steps in STEPS.items() for s in steps])
@pytest.mark.parametrize("cycle", [0, 1])
def test_all_steps_cycles_and_next_identity(module, step, cycle):
    f = frame()
    f.update(module_id=module, target_step_id=step, actual_step_id=step,
             target_phase=PHASES[module][step], actual_phase=PHASES[module][step],
             target_cycle_index=cycle, actual_cycle_index=cycle)
    r = make_material(f, evidence())
    assert r["truth"]["relation"] == "SAME_STEP"
    index = STEPS[module].index(step)
    next_index = (index + 1) % len(STEPS[module])
    assert r["truth"]["next_target"] == {
        "cycle_index": cycle + (next_index == 0), "step_id": STEPS[module][next_index]}


def test_target_counterfactual_does_not_rewrite_actual():
    f = frame()
    a = make_material(f, evidence())
    f.update(target_step_id="hold_2", target_phase="hold", target_cycle_index=4)
    b = make_material(f, evidence())
    assert a["truth"]["actual"] == b["truth"]["actual"]
    assert a["truth"]["display_actual"] == b["truth"]["display_actual"]
    assert a["answer_key"]["C-A1"]["value"] == b["answer_key"]["C-A1"]["value"]


def test_disconnection_hides_stale_actual_but_preserves_raw_identity():
    f = frame()
    f.update(resp_device_state="DISCONNECTED", fallback_state="UNUSABLE", fallback_reason="DEVICE_DISCONNECTED")
    r = make_material(f, evidence())
    assert r["truth"]["actual"] is not None
    assert r["truth"]["display_actual"] is None
    assert r["answer_key"]["C-D1"]["value"] == "DISCONNECTED"
    assert r["answer_key"]["C-D2"]["value"] == "TARGET_ONLY"


def test_missing_actual_source_and_partial_identity_rejected():
    with pytest.raises(ValueError, match="INDEPENDENT_ACTUAL_SOURCE_REQUIRED"):
        make_material(frame(), evidence(actual_source_ref=None))
    f = frame()
    f["actual_cycle_index"] = None
    with pytest.raises(Exception, match="INCOMPLETE_STEP_IDENTITY"):
        make_material(f, evidence())


def test_response_binds_seed_specific_material():
    a, b = [make_material(frame(), evidence(), seed=s) for s in (1, 2)]
    assert a["event_sha256"] == b["event_sha256"]
    assert a["material_sha256"] != b["material_sha256"]
    r = score_response(a, "C-T1", "RESPONDED", a["answer_key"]["C-T1"]["option_index"])
    assert r["material_sha256"] == a["material_sha256"]


def test_terminal_cumulative_is_not_forced_to_full_recovery():
    f = frame()
    f.update(segment="lock_transition", recovery_value=0.28, recovery_locked=True)
    r = make_material(f, evidence())
    assert r["truth"]["recovery_value"] == 0.28
    assert r["answer_key"]["C-C1"]["value"] == "mid"


def test_export_determinism_and_participant_key_separation():
    from srp_step_measurement.build_evidence import artifacts
    a, b = artifacts(), artifacts()
    assert a == b
    public = json.loads(a["participant_items.json"])
    private = json.loads(a["private_answer_keys.json"])
    assert len(public) == 15 and len(private) == 30
    for item in public:
        assert item["clip_id"].startswith("clip-") and item["clip_id"][5:].isdigit()
        assert set(item) == {"clip_id", "material_sha256", "items"}
        for question in item["items"]:
            assert set(question) == {"item_id", "layer", "prompt", "options"}
            assert all(word not in question["prompt"] for word in ("天气", "原生", "圆环", "控件"))


@pytest.mark.parametrize("module", list(STEPS))
def test_option_vocabulary_does_not_reveal_step_or_cycle(module):
    observed = []
    for cycle in [0, 1, 3]:
        for step in STEPS[module]:
            f = frame()
            f.update(module_id=module, target_step_id=step, actual_step_id=step,
                     target_phase=PHASES[module][step], actual_phase=PHASES[module][step],
                     target_cycle_index=cycle, actual_cycle_index=cycle)
            m = make_material(f, evidence())
            observed.append([{o["value"] for o in i["options"]} for i in m["items"][:3]])
    assert all(o == observed[0] for o in observed)
    assert observed[0][0] == set(STEPS[module]) | {"UNKNOWN"}


def test_option_positions_balanced_across_sixty_forms():
    for module in STEPS:
        f = frame()
        step = STEPS[module][0]
        f.update(module_id=module, target_step_id=step, actual_step_id=step,
                 target_phase=PHASES[module][step], actual_phase=PHASES[module][step])
        materials = [make_material(f, evidence(), seed=s) for s in range(60)]
        for item in materials[0]["items"]:
            n = len(item["options"])
            positions = [m["answer_key"][item["item_id"]]["option_index"] for m in materials]
            assert [positions.count(i) for i in range(n)] == [60 // n] * n


@pytest.mark.parametrize("mutation", ["options", "key", "seed"])
def test_tampered_material_cannot_score_with_original_hash(mutation):
    m = make_material(frame(), evidence())
    k = m["answer_key"]["C-T1"]["option_index"]
    if mutation == "options":
        choices = m["items"][0]["options"]
        j = (k + 1) % len(choices)
        choices[k], choices[j] = choices[j], choices[k]
    elif mutation == "key":
        m["answer_key"]["C-T1"]["option_index"] = 0
        m["answer_key"]["C-T1"]["value"] = "TAMPERED"
    else:
        m["seed"] += 1
    with pytest.raises(ValueError, match="MATERIAL_INTEGRITY_MISMATCH"):
        score_response(m, "C-T1", "RESPONDED", k)
