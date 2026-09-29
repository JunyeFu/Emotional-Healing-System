from __future__ import annotations

import random

import a03_gate2_spec.simulation as simulation
from a03_gate2_spec.simulation import Scenario, run_simulation


def test_simulation_is_deterministic_and_bounded():
    first = run_simulation(seed=17, replications=120)
    second = run_simulation(seed=17, replications=120)
    assert first == second
    for scenario in first["scenarios"].values():
        for analysis_set in simulation.ANALYSIS_SETS:
            analysis = scenario[analysis_set]
            assert all(0 <= value <= 1 for value in analysis["pass_probability"].values())
        assert 0 <= scenario["BOTH_ANALYSIS_SETS"]["joint_pass_probability"] <= 1


def test_simulation_covers_required_scenarios_and_analysis_sets():
    report = run_simulation(seed=21, replications=120)
    assert set(report["scenarios"]) == {
        "target", "null_manipulation", "ceiling", "differential_missing", "item_shift"
    }
    for scenario in report["scenarios"].values():
        assert set(scenario) == {
            "PRIMARY_CONSERVATIVE",
            "OBSERVED_CASE",
            "BOTH_ANALYSIS_SETS",
        }


def test_both_analysis_sets_share_each_generated_replication(monkeypatch):
    calls = 0
    original = simulation._participant

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(simulation, "_participant", counted)
    run_simulation(seed=4, replications=100, per_condition=2)
    assert calls == len(simulation.SCENARIOS) * 100 * 2 * 2


def test_timeout_is_represented_for_every_outcome():
    scenario = Scenario(
        "forced_timeout", 0.0, 0.5, 0.5, 4.0, 4.0, 0.1, 0.1,
        skipped_rate=0.0, timeout_rate=1.0, technical_rate=0.0,
    )
    row = simulation._participant(random.Random(3), scenario, native=True)
    assert set(row["scci_statuses"]) == {"TIMEOUT"}
    assert set(row["comprehension_statuses"]) == {"TIMEOUT"}
    assert row["effort_status"] == "TIMEOUT"
    assert row["stage_error_status"] == "TIMEOUT"


def test_differential_missing_scenario_has_condition_specific_rates():
    scenario = next(item for item in simulation.SCENARIOS if item.name == "differential_missing")
    assert scenario.native_missing_multiplier > 1.0


def test_output_cannot_be_mistaken_for_formal_calibration():
    report = run_simulation(seed=22, replications=120)
    assert report["evidence_class"] == "SYNTHETIC_ONLY"
    assert report["formal_margins"] is None
    assert report["formal_sample_size"] is None
    assert report["decision"].startswith("SYNTHETIC_SENSITIVITY_POINT_")


def test_scope_names_separate_anchor_from_complete_target():
    anchor = run_simulation(
        seed=22, replications=100, per_condition=85,
        decision_scope="existing_planning_anchor",
    )
    target = run_simulation(
        seed=22, replications=100, per_condition=96,
        decision_scope="complete_target",
    )
    assert anchor["decision"].startswith("SYNTHETIC_EXISTING_PLANNING_ANCHOR_")
    assert target["decision"].startswith("SYNTHETIC_COMPLETE_TARGET_")
    assert "RECRUITMENT_CAP_240_NOT_MODELED_AS_COMPLETE_OUTCOMES" in target["limitations"]
