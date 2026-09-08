"""Generate synthetic-only measurement fixtures and separate public/private materials."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from srp_step_measurement.measurement import CONFIG_PATH, PHASES, STEPS, make_material


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def cases():
    source = HERE.parent / "05-通信协议/contracts/consumer-fixtures/v2.2/unity/phase-instance-stream.jsonl"
    base = json.loads(source.read_text(encoding="utf-8").splitlines()[0])
    samples = []
    for module, steps in STEPS.items():
        for step in steps:
            f = deepcopy(base)
            f.update(module_id=module, target_step_id=step, actual_step_id=step,
                     target_phase=PHASES[module][step], actual_phase=PHASES[module][step])
            samples.append((f"{module}-{step}", f, "SAME_STEP"))
    for name, module, target, actual in [
        ("hold-swap", "storm", "hold_2", "hold_1"),
        ("second-inhale-missing", "fade", "inhale_2", "inhale_1"),
    ]:
        f = deepcopy(base)
        f.update(module_id=module, target_step_id=target, actual_step_id=actual,
                 target_phase=PHASES[module][target], actual_phase=PHASES[module][actual])
        samples.append((name, f, "DIFFERENT_STEP"))
    f = deepcopy(base)
    f.update(actual_step_id=None, actual_cycle_index=None, actual_phase="none", actual_progress=0,
             resp_device_state="DISCONNECTED", fallback_state="UNUSABLE", fallback_reason="DEVICE_DISCONNECTED")
    samples.append(("actual-unknown-disconnected", f, "UNKNOWN"))
    f = deepcopy(base)
    f.update(actual_cycle_index=1, actual_step_id=f["target_step_id"], actual_phase=f["target_phase"])
    samples.append(("wrong-cycle", f, "DIFFERENT_CYCLE"))
    return samples


def artifacts():
    inputs, public, private, results = [], [], [], []
    for case_index, (event_id, frame, expected) in enumerate(cases()):
        evidence = {"event_id": event_id, "source_kind": "SYNTHETIC_FIXTURE",
                    "actual_source_ref": "fixture:independent-actual" if frame["actual_step_id"] else None,
                    "actual_unknown_reason": None if frame["actual_step_id"] else "DEVICE_DISCONNECTED",
                    "clip_duration_ns": 4_000_000_000, "cumulative_band": "mid",
                    "cumulative_annotation_ref": "fixture:band-v1", "previous_recovery_value": 0.25}
        inputs.append({"frame": frame, "evidence": evidence, "expected_relation": expected})
        pair = []
        for mode in ("scene_native", "abstract_pacer"):
            f = dict(frame, cue_mode=mode)
            m = make_material(f, evidence, seed=20260908)
            assert m["truth"]["relation"] == expected
            pair.append(m)
            private.append({"event_id": event_id, "public_clip_id": f"clip-{case_index + 1:03d}", "condition": mode, **m})
        assert pair[0]["items"] == pair[1]["items"]
        assert pair[0]["answer_key"] == pair[1]["answer_key"]
        # No condition labels, truth or key in the participant-facing file.
        public.append({"clip_id": f"clip-{case_index + 1:03d}", "material_sha256": pair[0]["material_sha256"],
                       "items": pair[0]["items"]})
        results.append({"event_id": event_id, "expected_relation": expected, "status": "PASS",
                        "condition_pair_equal": True, "clip_render_review": "PENDING"})
    sources = [CONFIG_PATH, HERE / "measurement.py", Path(__file__),
               HERE.parent / "05-通信协议/contracts/runtime-contract-v2.2.schema.json",
               HERE.parents[1] / "00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/03_步骤02_构念比较条件与测量/01_F-02_Gate2构念与测量深度研究包_v0.9-candidate.md"]
    source_hashes = {p.relative_to(HERE.parents[1]).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in sources}
    output = {"input_cases.json": inputs, "participant_items.json": public, "private_answer_keys.json": private,
              "verification.json": {"evidence_class": "SYNTHETIC_ONLY", "case_count": len(results),
                                   "source_text_sha256_lf": source_hashes, "cases": results,
                                   "real_annotation_validated": False, "formal_ready": False}}
    data = {name: encoded(value) for name, value in output.items()}
    data["sha256.json"] = encoded({name: hashlib.sha256(value).hexdigest() for name, value in data.items()})
    return data


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    output = HERE / "evidence"
    data = artifacts()
    if args.check:
        for name, content in data.items():
            if (output / name).read_bytes() != content:
                raise ValueError("EVIDENCE_DRIFT:" + name)
        print("PASS: deterministic synthetic materials and byte hashes")
    else:
        output.mkdir(exist_ok=True)
        for name, content in data.items():
            (output / name).write_bytes(content)
        print("WROTE: 15 synthetic cases, 30 condition materials; render/real annotation pending")


if __name__ == "__main__":
    main()
