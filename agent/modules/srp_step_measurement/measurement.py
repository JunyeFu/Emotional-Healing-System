"""Generate condition-neutral step-instance questions from independent event facts."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib import import_module
import json
import math
from pathlib import Path
import random

from srp_session_core.contract_adapter import validate_message

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "srp_session_core/config/breath_protocol_config_v2.2.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
STEPS = {m: tuple(s["step_id"] for s in v["steps"]) for m, v in CONFIG["modules"].items()}
PHASES = import_module("05-通信协议.runtime_contract_v22").STEP_PHASES
VERSION = "u12-02-candidate-1"
UNKNOWN = "UNKNOWN"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def identity(frame, prefix):
    cycle, step = frame[f"{prefix}_cycle_index"], frame[f"{prefix}_step_id"]
    return None if cycle is None else {"cycle_index": int(cycle), "step_id": step}


def next_identity(module, current):
    if current is None:
        return None
    steps = STEPS[module]
    index = steps.index(current["step_id"]) + 1
    return {"cycle_index": current["cycle_index"] + (index == len(steps)),
            "step_id": steps[index % len(steps)]}


def step_label(module, value):
    if value == UNKNOWN:
        return "当前信息不足，无法确定"
    names = {"inhale_1": "第一次吸气" if module == "fade" else "吸气",
             "inhale_2": "第二次吸气（补吸）", "hold_1": "吸气后的停留",
             "exhale_1": "呼气", "hold_2": "呼气后的停留"}
    return names[value]


def identity_options(module):
    # The full protocol vocabulary is independent of the answer and of the cycle.
    return [(v, step_label(module, v)) for v in (*STEPS[module], UNKNOWN)]


def _require_context(evidence):
    for field in ("event_id", "cumulative_annotation_ref"):
        if not isinstance(evidence.get(field), str) or not evidence[field].strip():
            raise ValueError("MISSING_EVIDENCE:" + field)
    if evidence.get("source_kind") not in {"SYNTHETIC_FIXTURE", "RECORDED_ANNOTATION"}:
        raise ValueError("SOURCE_KIND_REQUIRED")
    duration = evidence.get("clip_duration_ns")
    if type(duration) is not int or duration <= 0:
        raise ValueError("INVALID_CLIP_DURATION")
    if evidence.get("cumulative_band") not in {"low", "mid", "high", "unknown"}:
        raise ValueError("CUMULATIVE_BAND_REQUIRED")
    previous = evidence.get("previous_recovery_value")
    if previous is not None and (isinstance(previous, bool) or not isinstance(previous, (int, float))
                                 or not math.isfinite(previous) or not 0 <= previous <= 1):
        raise ValueError("INVALID_PREVIOUS_RECOVERY")


def make_material(frame, evidence, *, seed=0):
    """Return items plus a private answer key; no participant interaction or I/O."""
    if frame.get("schema_version") != "2.2":
        raise ValueError("STEP_INSTANCE_REQUIRES_V22")
    f = validate_message("telemetry_frame", frame)
    _require_context(evidence)
    if type(seed) is not int:
        raise ValueError("INTEGER_SEED_REQUIRED")
    module = f["module_id"]
    target, actual = identity(f, "target"), identity(f, "actual")
    reason = evidence.get("actual_unknown_reason")
    if actual is None and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("ACTUAL_UNKNOWN_REASON_REQUIRED")
    if actual is not None and (not isinstance(evidence.get("actual_source_ref"), str)
                               or not evidence["actual_source_ref"].strip()):
        raise ValueError("INDEPENDENT_ACTUAL_SOURCE_REQUIRED")
    if actual is not None and reason is not None:
        raise ValueError("KNOWN_ACTUAL_WITH_UNKNOWN_REASON")
    available = actual is not None and f["fallback_state"] == "GOOD" and f["resp_device_state"] == "CONNECTED"
    visible_actual = actual if available else None
    if target is None or visible_actual is None:
        relation = UNKNOWN
    elif target["cycle_index"] != actual["cycle_index"]:
        relation = "DIFFERENT_CYCLE"
    elif target["step_id"] != actual["step_id"]:
        relation = "DIFFERENT_STEP"
    else:
        relation = "SAME_STEP"
    previous = evidence.get("previous_recovery_value")
    trend = UNKNOWN if previous is None else (
        "INCREASED" if f["recovery_value"] > previous else
        "DECREASED" if f["recovery_value"] < previous else "UNCHANGED")
    availability = ("BOTH" if available else "TARGET_ONLY") if target is not None else (
        "ACTUAL_ONLY" if available else "NEITHER")
    limitation = ("DISCONNECTED" if f["resp_device_state"] == "DISCONNECTED" else
                  "INPUT_LIMITED" if not available else "AVAILABLE")
    following = next_identity(module, target)
    truth = {"module_id": module, "target": target, "actual": actual,
             "display_actual": visible_actual, "next_target": following,
             "relation": relation, "actual_unknown_reason": reason,
             "fallback_state": f["fallback_state"], "fallback_reason": f["fallback_reason"],
             "resp_device_state": f["resp_device_state"],
             "recovery_value": f["recovery_value"], "recovery_locked": f["recovery_locked"]}
    specs = [
        ("C-T1", "target", "片段结束时，当前目标属于哪个具体步骤？",
         target["step_id"] if target else UNKNOWN, identity_options(module)),
        ("C-T2", "target", "按目标结构，当前目标之后的下一个步骤是什么？",
         following["step_id"] if following else UNKNOWN, identity_options(module)),
        ("C-A1", "actual", "片段结束时，显示的实际状态属于哪个具体步骤？",
         visible_actual["step_id"] if visible_actual else UNKNOWN, identity_options(module)),
        ("C-A2", "actual", "片段结束时，实际与目标的步骤身份是什么关系？", relation,
         [("SAME_STEP", "同一轮的同一步骤"), ("DIFFERENT_STEP", "同一轮的不同步骤"),
          ("DIFFERENT_CYCLE", "处于不同轮次"), (UNKNOWN, "当前信息不足")]),
        ("C-C1", "cumulative", "片段结束时，显示的累计信息处于哪个区间？",
         evidence["cumulative_band"],
         [("low", "较低区间"), ("mid", "中间区间"), ("high", "较高区间"), ("unknown", "当前信息不足")]),
        ("C-C2", "cumulative", "与片段起点相比，结束时显示的累计值怎样变化？", trend,
         [("INCREASED", "升高"), ("DECREASED", "降低"), ("UNCHANGED", "不变"), (UNKNOWN, "当前信息不足")]),
        ("C-D1", "degraded", "片段结束时，实际信息的可用情况是什么？", limitation,
         [("AVAILABLE", "当前可读取"), ("INPUT_LIMITED", "输入受限，不能可靠读取"),
          ("DISCONNECTED", "采集连接已中断"), (UNKNOWN, "片段未提供可判断的信息")]),
        ("C-D2", "degraded", "片段结束时，哪些步骤信息仍可可靠读取？", availability,
         [("BOTH", "目标与实际"), ("TARGET_ONLY", "仅目标"),
          ("ACTUAL_ONLY", "仅实际"), ("NEITHER", "两者均不可读取")]),
    ]
    event_hash = digest({"truth": truth, "evidence": evidence, "config": CONFIG, "version": VERSION})
    rng = random.Random(f"{seed}:{event_hash}")
    items, key = [], {}
    for item_id, layer, prompt, correct, choices in specs:
        offset = int(digest({"event": event_hash, "item": item_id})[:8], 16)
        position = (offset + seed) % len(choices)
        correct_option = next(c for c in choices if c[0] == correct)
        others = [c for c in choices if c[0] != correct]
        rng.shuffle(others)
        others.insert(position, correct_option)
        if len(others) != len(choices) or len({c[0] for c in others}) != len(choices):
            raise ValueError("INVALID_ITEM_OPTIONS:" + item_id)
        items.append({"item_id": item_id, "layer": layer, "prompt": prompt,
                      "options": [{"value": v, "label": label} for v, label in others]})
        key[item_id] = {"value": correct, "option_index": position}
    material_hash = digest({"event_sha256": event_hash, "items": items, "answer_key": key, "seed": seed})
    return {"version": VERSION, "event_sha256": event_hash, "material_sha256": material_hash, "seed": seed,
            "source_frame_sha256": digest(frame), "evidence_class": evidence["source_kind"],
            "collection_timing": "AFTER_POST_PANAS", "formal_measurement_validated": False,
            "truth": truth, "evidence": deepcopy(evidence), "items": items, "answer_key": key}


def score_response(material, item_id, status, option_index):
    """Preserve missingness; downstream analysis chooses its frozen policy."""
    expected = digest({k: material[k] for k in ("event_sha256", "items", "answer_key", "seed")})
    if expected != material["material_sha256"]:
        raise ValueError("MATERIAL_INTEGRITY_MISMATCH")
    if item_id not in material["answer_key"]:
        raise ValueError("UNKNOWN_ITEM")
    if status not in {"RESPONDED", "SKIPPED", "TIMEOUT", "TECH_UNPRESENTED"}:
        raise ValueError("INVALID_RESPONSE_STATUS")
    if status == "RESPONDED":
        item = next(i for i in material["items"] if i["item_id"] == item_id)
        if type(option_index) is not int or not 0 <= option_index < len(item["options"]):
            raise ValueError("INVALID_OPTION_INDEX")
        correct = int(option_index == material["answer_key"][item_id]["option_index"])
    else:
        if option_index is not None:
            raise ValueError("NONRESPONSE_HAS_VALUE")
        correct = None
    return {"item_id": item_id, "status": status, "option_index": option_index,
            "correct": correct, "event_sha256": material["event_sha256"],
            "material_sha256": material["material_sha256"],
            "material_version": material["version"]}
