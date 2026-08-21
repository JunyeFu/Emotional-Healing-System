from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest


MODULE_ROOT = Path(__file__).resolve().parents[2]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))


@pytest.fixture
def manifest_factory():
    def build(*, session_id: str = "S-P02-0001", runtime_mode: str = "dev_replay"):
        manifest = {
            "schema_version": "2.1",
            "message_type": "session_manifest",
            "research_id": "SRP-R-0123456789abcdef0123456789abcdef",
            "session_id": session_id,
            "study_stage": "stage_1",
            "runtime_mode": runtime_mode,
            "cue_mode": "scene_native",
            "assignment_arm": "scene_native",
            "allocation_index": 7,
            "randomization_stratum": "na_pre_low",
            "randomization_block": 1,
            "randomization_list_hash": "sha256:p02-list",
            "weather_sequence": ["storm", "heat", "snow", "fade"],
            "module_durations": {
                "demo": 25,
                "closed_loop": 150,
                "lock_transition": 25,
            },
            "protocol_config_version": "1.1",
            "randomization_version": "1.0",
            "strategy_version": None,
            "device_config": {
                "resp": {"source": "none"},
                "ecg": {"source": "none"},
            },
            "unity_build_hash": "sha256:unity-p02-fixture",
            "python_commit": "p02-fixture",
            "td_build_hash": None,
            "source_policy": "replay",
            "created_utc": "2026-08-16T00:00:00Z",
        }
        if runtime_mode.startswith("formal_"):
            manifest["source_policy"] = "real"
            manifest["device_config"] = {
                "resp": {"source": "plux_respiban", "serial": "configured"},
                "ecg": {"source": "polar_h10", "serial": "configured"},
            }
        return deepcopy(manifest)

    return build


@pytest.fixture
def assignment_factory():
    from srp_session_core import AssignmentBundle

    def build(manifest):
        sequence = tuple(manifest["weather_sequence"])
        remaining = list(sequence)
        decisions = []
        for position, selected in enumerate(sequence):
            candidates = list(remaining)
            decisions.append(
                {
                    "schema_version": "2.1",
                    "message_type": "policy_decision",
                    "decision_id": f"PD-P02-{position}",
                    "session_id": manifest["session_id"],
                    "stage": manifest["study_stage"],
                    "position": position,
                    "candidate_actions": candidates,
                    "selected_action": selected,
                    "behavior_probability": 1 / len(candidates),
                    "target_policy_probability": None,
                    "state_snapshot_hash": f"sha256:state-{position}",
                    "random_draw": position / 10,
                    "reason_code": "FIXED_SEQUENCE_ASSIGNMENT",
                    "fallback_applied": False,
                    "fallback_reason": None,
                    "policy_version": None,
                    "created_monotonic_ns": position,
                }
            )
            remaining.remove(selected)
        return AssignmentBundle(
            allocation_index=manifest["allocation_index"],
            randomization_list_hash=manifest["randomization_list_hash"],
            weather_sequence=sequence,
            policy_decisions=tuple(decisions),
            permit_id="PERMIT-P02",
            reservation_id="RES-P02",
        )

    return build
