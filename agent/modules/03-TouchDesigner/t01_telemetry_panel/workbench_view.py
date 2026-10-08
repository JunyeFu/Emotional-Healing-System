"""Read-only presentation model shared by host tests and native TD panels."""
from __future__ import annotations

from collections.abc import Mapping
import json

MISSING = "—"
LABELS = {
    "WAITING": "等待遥测", "LIVE": "正在接收", "DISCONNECTED": "断流",
    "CONNECTED": "已连接", "DEGRADED": "降级", "UNUSABLE": "不可用", "GOOD": "正常",
    "scene_native": "场景原生提示", "abstract_pacer": "抽象呼吸提示",
    "storm": "风雨", "heat": "炎热", "snow": "冰雪", "fade": "褪色",
    "demo": "示范段", "closed_loop": "闭环段", "lock_transition": "锁定过渡段",
    "inhale": "吸气", "exhale": "呼气", "hold": "保持", "recovery": "恢复", "none": "无",
}
OVERVIEW_LABELS = dict(LABELS, dev_replay="开发回放", dev_mock="合成输入",
                       formal_stage_1="阶段一正式", formal_stage_3="阶段三正式")
COUNTERS = (
    ("accepted_frames", "有效接收"), ("lost_frames", "序号缺口"),
    ("duplicate_frames", "重复帧"), ("out_of_order_frames", "乱序帧"),
    ("invalid_frames", "无效帧"), ("reconnect_count", "重连"),
)
CONTEXT = (
    ("session_id", "会话 ID"), ("runtime_mode", "运行模式"), ("schema_version", "协议版本"),
    ("module_id", "天气模块"), ("module_position", "模块位置"),
    ("segment", "流程段"), ("cue_mode", "提示条件"),
)


def display(value, *, percent=False, translated=False):
    if value is None or value == "UNAVAILABLE":
        return MISSING
    if isinstance(value, bool):
        return "是" if value else "否"
    if percent:
        return f"{value * 100:.1f}%"
    if translated and value in LABELS:
        return f"{LABELS[value]} ({value})"
    return str(value)


def compact(text, limit=42):
    """Full strings remain available in the independently scrollable details page."""
    return text if len(text) <= limit else text[:limit - 1] + "…"


def flatten(mapping, prefix=""):
    result = {}
    for key, value in mapping.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            result.update(flatten(value, path))
        else:
            result[path] = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, tuple)) else display(value)
    return result


def view_model(snapshot):
    t = snapshot.telemetry
    local = snapshot.display_only["transport"]
    state = snapshot.meta["stream_state"]
    status = LABELS[state]
    if state == "DISCONNECTED":
        status += " · 末帧历史值"
    if t.get("runtime_mode") == "dev_replay":
        status += " · 开发回放"
    elif t.get("runtime_mode") == "dev_mock":
        status += " · 合成输入"
    values = {"status": status}
    values.update({key: display(t.get(key), translated=True) for key, _ in CONTEXT})
    for source in ("resp", "ecg"):
        values[f"{source}_state"] = display(t.get(f"{source}_device_state"), translated=True) if t else "未知"
        values[f"{source}_sqi"] = display(t.get("signal_quality", {}).get(source), percent=True)
    for side in ("target", "actual"):
        for field in ("cycle_index", "step_id", "phase", "progress"):
            key = f"{side}_{field}"
            values[key] = display(t.get(key), percent=field == "progress", translated=field == "phase")
    for key in ("actual_confidence", "recovery_value", "recovery_locked", "fallback_state", "fallback_reason"):
        values[key] = display(t.get(key), percent=key == "actual_confidence", translated=key == "fallback_state")
    values["last_error"] = display(local.get("last_error"))
    values.update({key: display(local[key]) for key, _ in COUNTERS})
    values["footer"] = f"TD 末帧年龄 {display(local.get('frame_age_ms'))} ms    帧序号 {display(t.get('frame_seq'))}"
    details = flatten({"telemetry": t, "display_only": snapshot.display_only, "meta": snapshot.meta})
    overview_values = dict(values)
    for key, _ in CONTEXT:
        value = t.get(key)
        overview_values[key] = OVERVIEW_LABELS.get(value, display(value))
    for source in ("resp", "ecg"):
        value = t.get(f"{source}_device_state")
        label = '设备断连' if value == 'DISCONNECTED' else LABELS.get(value, display(value))
        overview_values[f"{source}_state"] = label if t else "未知"
        if state == 'DISCONNECTED' and t:
            overview_values[f"{source}_state"] = '末帧：' + ('断连' if value == 'DISCONNECTED' else label)
            overview_values[f"{source}_sqi"] = '历史 ' + values[f"{source}_sqi"]
        elif value in ('DISCONNECTED', 'UNUSABLE'):
            overview_values[f"{source}_sqi"] = '不可用'
    steps = {'inhale_1': '第一次吸气', 'inhale_2': '第二次吸气',
             'exhale_1': '呼气', 'hold_1': '第一次保持', 'hold_2': '第二次保持'}
    for side in ('target', 'actual'):
        key = side + '_step_id'
        overview_values[key] = steps.get(t.get(key), display(t.get(key)))
    for side in ("target", "actual"):
        value = t.get(f"{side}_phase")
        overview_values[f"{side}_phase"] = LABELS.get(value, display(value))
    value = t.get("fallback_state")
    overview_values["fallback_state"] = LABELS.get(value, display(value))
    return {"values": values, "overview_values": overview_values,
            "details": details, "state": state}
