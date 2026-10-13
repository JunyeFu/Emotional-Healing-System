from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image

from render_h2_v10 import require, sha256


HERE = Path(__file__).resolve().parent
REPO = next(parent for parent in (HERE, *HERE.parents) if (parent / ".git").exists())
CONFIG_PATH = HERE / "V-04_H3合并评审配置_v1.0.json"
LOCK_PATH = HERE / "V-04_toolchain-lock_v1.0.json"
STORYBOARD_PATH = HERE / "V-04_H3_四天气六节点Unity交接分镜_v1.0.json"
MANIFEST_PATH = HERE / "V-04_H3合并评审候选清单_v1.0.json"
REPORT_PATH = HERE / "V-04_H3合并评审机器验收记录_v1.0.json"
EXPECTED_OUTPUT_ROOT = REPO / ".artifacts-local/V-04/H3/combined-review-candidate-v1"
EXPECTED_KEYFRAME_PATH = HERE / "review/H3/V-04-H3-combined-review-keyframes-v1.jpg"
EXPECTED_STORYBOARD_SHEET_PATH = HERE / "review/H3/V-04-H3-six-node-storyboard-v1.jpg"


def nested_value(document: dict[str, object], dotted_path: str) -> object:
    value: object = document
    for part in dotted_path.split("."):
        require(isinstance(value, dict) and part in value, f"missing gate evidence field: {dotted_path}")
        value = value[part]
    return value


def stream(probe: dict[str, object], kind: str) -> dict[str, object]:
    matches = [item for item in probe["streams"] if item.get("codec_type") == kind]
    require(len(matches) == 1, f"expected one {kind} stream")
    return matches[0]


def validate_storyboard(config: dict[str, object], storyboard: dict[str, object]) -> None:
    required_weather = config["machine_gates"]["required_weather_ids"]
    required_nodes = config["machine_gates"]["required_node_ids"]
    required_times = config["machine_gates"]["required_node_times_s"]
    weather_rows = storyboard["weather_storyboards"]
    require([item["technical_id"] for item in weather_rows] == required_weather, "weather order or set drift")
    require(storyboard["recommended_timeline"]["unity_must_not_own_clock"] is True, "Unity clock boundary drift")
    timeline = storyboard["recommended_timeline"]
    require(
        [timeline["demo_s"], timeline["closed_loop_s"], timeline["lock_transition_s"], timeline["module_total_s"]]
        == [25.0, 150.0, 25.0, 200.0],
        "recommended timeline drift",
    )
    require(
        timeline["allowed_ranges_s"]
        == {"demo": [24.0, 30.0], "closed_loop": [140.0, 160.0], "lock_transition": [20.0, 30.0]},
        "allowed timeline ranges drift",
    )
    rules = storyboard["global_rules"]
    require(rules["participant_input"] == "NONE_DURING_CORE_EXPERIENCE", "participant input boundary drift")
    require(rules["sequence_authority"] == "PYTHON_SESSION_CORE_AND_MANIFEST", "sequence authority drift")
    require(rules["transition_sequence_binding"] is False, "transition bound a weather sequence")
    require("NO_ZERO_FILL" in rules["failure_rule"], "failure truth rule drift")
    require(rules["asset_rule"] == "TEMP_REFERENCE_ONLY_UNTIL_G02_LICENSE_GATE", "asset rule drift")
    require(rules["reference_sample_semantics"] == "STYLE_ONLY_NOT_RUNTIME_CAPTURE", "style reference semantics drift")

    require(storyboard["status"] == "MACHINE_PASS_READY_FOR_INDEPENDENT_REVIEW", "storyboard status drift")
    require(
        rules["demo_cycle_identity_gate"] == "F-05_V2_2_REQUIRED_FOR_ALL_FOUR_WEATHERS",
        "all-weather demo cycle gate drift",
    )
    receipt = storyboard["f01_render_receipt_contract"]
    require(
        receipt["required_fields"]
        == [
            "schema_version",
            "message_type",
            "receipt_id",
            "session_id",
            "event_id",
            "frame_seq",
            "unity_frame",
            "rendered_monotonic_ns",
            "module_id",
            "segment",
            "result",
            "error_code",
        ],
        "F-01 render receipt fields drift",
    )
    require(
        receipt["accepted_control_type"] == "segment"
        and receipt["requires_acknowledged_control"] is True
        and receipt["module_and_segment_must_match_control_payload"] is True,
        "F-01 render receipt binding drift",
    )
    require(
        receipt["adjacent_node_evidence_fields"]
        == ["cue_mode", "build_hash", "screenshot_path", "telemetry_frame_seq"],
        "adjacent node evidence fields drift",
    )
    expected_templates = {
        "ENTRY": {
            "visual_segment": "demo",
            "boundary_side": "AFTER_CURRENT_DEMO_SEGMENT_APPLIED",
            "visual_snapshot": "FIRST_FRAME_AFTER_CURRENT_DEMO_CONTROL",
            "control_type": "segment",
            "control_module_relation": "CURRENT",
            "control_segment": "demo",
            "ack_required": True,
            "render_receipt_required": True,
        },
        "DEMO_END": {
            "visual_segment": "demo",
            "boundary_side": "IMMEDIATELY_BEFORE_CLOSED_LOOP_CONTROL",
            "visual_snapshot": "LAST_CURRENT_DEMO_TELEMETRY_FRAME",
            "control_type": None,
            "control_module_relation": "CURRENT",
            "control_segment": None,
            "ack_required": False,
            "render_receipt_required": False,
        },
        "CLOSED_LOOP_START": {
            "visual_segment": "closed_loop",
            "boundary_side": "AFTER_CURRENT_CLOSED_LOOP_SEGMENT_APPLIED",
            "visual_snapshot": "FIRST_FRAME_AFTER_CURRENT_CLOSED_LOOP_CONTROL",
            "control_type": "segment",
            "control_module_relation": "CURRENT",
            "control_segment": "closed_loop",
            "ack_required": True,
            "render_receipt_required": True,
        },
        "CLOSED_LOOP_MID": {
            "visual_segment": "closed_loop",
            "boundary_side": "MID_SEGMENT_TELEMETRY_CHECKPOINT",
            "visual_snapshot": "CURRENT_CLOSED_LOOP_TELEMETRY_FRAME",
            "control_type": None,
            "control_module_relation": "CURRENT",
            "control_segment": None,
            "ack_required": False,
            "render_receipt_required": False,
        },
        "CLOSED_LOOP_END": {
            "visual_segment": "closed_loop",
            "boundary_side": "LAST_FRAME_BEFORE_LOCK_TRANSITION_THEN_CONTROL",
            "visual_snapshot": "LAST_CURRENT_CLOSED_LOOP_TELEMETRY_FRAME",
            "control_type": "segment",
            "control_module_relation": "CURRENT",
            "control_segment": "lock_transition",
            "ack_required": True,
            "render_receipt_required": True,
        },
        "TRANSITION_COMPLETE": {
            "visual_segment": "lock_transition",
            "boundary_side": "LAST_FRAME_BEFORE_MODULE_ADVANCE_OR_END",
            "visual_snapshot": "LAST_CURRENT_LOCK_TRANSITION_FRAME",
            "non_final_control_sequence": ["module:NEXT", "segment:NEXT:demo"],
            "non_final_ack_required": True,
            "non_final_render_receipt": "REQUIRED_FOR_NEXT_DEMO_SEGMENT",
            "final_control_sequence": ["end:CURRENT"],
            "final_ack_required": True,
            "final_render_receipt": "NOT_ACCEPTED_FOR_END_CONTROL",
        },
    }
    require(storyboard["node_evidence_templates"] == expected_templates, "node evidence templates drift")

    node_required_fields = {
        "node_id",
        "module_time_s",
        "visual_segment",
        "boundary_side",
        "purpose",
        "target_state",
        "actual_state",
        "recovery_state",
        "fallback_state",
        "background_state",
        "authoritative_inputs",
        "condition_contract",
        "audio_state",
        "acceptance",
        "reference_sample",
    }
    expected_core_bindings = {
        "storm": "F-05_V2_2_REQUIRED",
        "heat": "V2_1_COARSE_PHASE_DIRECT",
        "snow": "V2_1_COARSE_PHASE_DIRECT",
        "fade": "F-05_V2_2_REQUIRED",
    }
    for weather in weather_rows:
        technical_id = weather["technical_id"]
        nodes = weather["nodes"]
        require([node["node_id"] for node in nodes] == required_nodes, f"{technical_id} node set drift")
        require([node["module_time_s"] for node in nodes] == required_times, f"{technical_id} node timing drift")
        binding = weather["runtime_binding"]
        require(binding["core_phase_animation"] == expected_core_bindings[technical_id], f"{technical_id} core binding drift")
        require(binding["demo_cycle_identity"] == "F-05_V2_2_REQUIRED", f"{technical_id} demo cycle gate drift")
        require(
            binding["formal_six_node_handoff"] == "F-05_V2_2_AND_CONSUMER_MIGRATION_REQUIRED",
            f"{technical_id} formal handoff gate drift",
        )
        require(len(weather["carriers"]) == 8, f"{technical_id} carrier map incomplete")
        for index, node in enumerate(nodes):
            require(node_required_fields.issubset(node), f"{technical_id}/{node['node_id']} contract incomplete")
            require("segment" not in node, f"{technical_id}/{node['node_id']} ambiguous segment field")
            template = expected_templates[node["node_id"]]
            require(node["visual_segment"] == template["visual_segment"], f"{technical_id}/{node['node_id']} visual segment drift")
            require(node["boundary_side"] == template["boundary_side"], f"{technical_id}/{node['node_id']} boundary semantics drift")
            require(bool(node["authoritative_inputs"]), f"{technical_id}/{node['node_id']} inputs missing")
            require(
                not {"module_index", "weather_id"}.intersection(node["authoritative_inputs"]),
                f"{technical_id}/{node['node_id']} uses non-contract runtime identifiers",
            )
            reference = node["reference_sample"]
            expected_source = technical_id if index < 5 else "corridor"
            require(reference["source"] == expected_source, f"{technical_id}/{node['node_id']} reference source drift")
            if index < 5:
                require(
                    float(reference["progress"]) == float(config["weather_style_reference_progress"]),
                    f"{technical_id}/{node['node_id']} style reference must be time-neutral",
                )
            else:
                require(0.0 <= float(reference["progress"]) <= 1.0, f"{technical_id}/{node['node_id']} progress invalid")
        require(nodes[0]["actual_state"] == "HIDDEN_FIRST_TARGET_CYCLE_DATA_STILL_RECORDED", f"{technical_id} demo rule drift")
        require(nodes[1]["recovery_state"] == "MODULE_BASELINE_LOCKED", f"{technical_id} demo recovery drift")
        require(nodes[2]["target_state"] == "CONTINUOUS_NO_RESET", f"{technical_id} boundary continuity drift")
        require(nodes[4]["recovery_state"] == "LOCK_LAST_VALUE_NO_PERFECT_ENDPOINT", f"{technical_id} lock rule drift")
        require(nodes[5]["condition_contract"] == "EXACT_SHARED_TRANSITION_NO_CUE_LAYERS", f"{technical_id} transition parity drift")
    fade = next(item for item in weather_rows if item["technical_id"] == "fade")
    require(fade["camera_mode"] == "FIXED", "fade camera must remain fixed")
    color = fade["shared_full_frame_color_rule"]
    require(color["reads_breath_step"] is False and color["reads_recovery_value"] is False, "fade color coupling drift")
    require(color["shared_between_conditions"] is True, "fade color condition parity drift")
    for weather in weather_rows:
        if weather["technical_id"] != "fade":
            require(weather["camera_mode"] == "HORIZONTAL_SCROLL", f"{weather['technical_id']} camera mode drift")
    require(sum(len(item["nodes"]) for item in weather_rows) == 24, "storyboard must contain 24 nodes")


def validate_image(entry: dict[str, object], expected_path: Path, expected_size: tuple[int, int]) -> None:
    path = HERE / entry["file"]
    require(path.resolve() == expected_path.resolve(), f"review image output path drift: {path}")
    require(path.is_file(), f"review image missing: {path}")
    require(path.stat().st_size == entry["size_bytes"] and sha256(path) == entry["sha256"], f"review image drift: {path.name}")
    with Image.open(path) as image:
        require(image.size == expected_size, f"review image size drift: {path.name}")


def validate_media_health(ffmpeg: Path, video: Path) -> None:
    decode = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-v", "error", "-i", str(video), "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(decode.returncode == 0 and not decode.stderr.strip(), "combined video decode errors detected")
    black = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(video),
            "-vf",
            "blackdetect=d=0.10:pix_th=0.04:pic_th=0.98",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require("black_start" not in black.stderr, "unexpected black interval detected")


def validate_manifest(config: dict[str, object], manifest: dict[str, object]) -> Path:
    require(manifest["candidate_id"] == config["candidate_id"], "manifest identity drift")
    require(manifest["config_sha256"] == sha256(CONFIG_PATH), "config hash drift")
    require(manifest["design_contract_sha256"] == sha256(HERE / config["design_contract"]), "design contract hash drift")
    require(manifest["storyboard_json_sha256"] == sha256(STORYBOARD_PATH), "storyboard JSON hash drift")
    require(manifest["storyboard_markdown_sha256"] == sha256(HERE / config["storyboard_markdown"]), "storyboard Markdown hash drift")
    require(
        manifest["unity_handoff_checklist_sha256"] == sha256(HERE / config["unity_handoff_checklist"]),
        "Unity checklist hash drift",
    )
    require(manifest["review_order_is_runtime_sequence"] is False, "manifest review order bound runtime sequence")
    source_sections = manifest["source_sections"]
    require([item["section_id"] for item in source_sections] == config["machine_gates"]["required_section_order"], "source section order drift")
    for source_entry, config_entry in zip(source_sections, config["sections"], strict=True):
        source = REPO / config_entry["source_file"]
        source_manifest = HERE / config_entry["source_manifest"]
        gate_evidence = config_entry["gate_evidence"]
        gate_evidence_path = HERE / gate_evidence["file"]
        require(source.is_file() and sha256(source) == config_entry["source_sha256"], f"{config_entry['section_id']} media drift")
        require(gate_evidence_path.resolve().parent == HERE.resolve(), f"{config_entry['section_id']} unsafe gate evidence path")
        require(gate_evidence_path.is_file(), f"{config_entry['section_id']} gate evidence missing")
        gate_document = json.loads(gate_evidence_path.read_text(encoding="utf-8"))
        for dotted_path, expected in gate_evidence["assertions"].items():
            require(
                nested_value(gate_document, dotted_path) == expected,
                f"{config_entry['section_id']} gate assertion failed: {dotted_path}",
            )
        require(
            nested_value(gate_document, gate_evidence["media_sha256_path"]) == config_entry["source_sha256"],
            f"{config_entry['section_id']} gate media hash drift",
        )
        require(source_entry["source_sha256"] == config_entry["source_sha256"], f"{config_entry['section_id']} recorded hash drift")
        require(source_entry["source_manifest_sha256"] == sha256(source_manifest), f"{config_entry['section_id']} manifest drift")
        require(source_entry["source_gate"] == config_entry["source_gate"], f"{config_entry['section_id']} source gate label drift")
        require(source_entry["gate_evidence_file"] == gate_evidence["file"], f"{config_entry['section_id']} gate file drift")
        require(source_entry["gate_evidence_sha256"] == sha256(gate_evidence_path), f"{config_entry['section_id']} gate record drift")
        require(source_entry["gate_assertions"] == gate_evidence["assertions"], f"{config_entry['section_id']} gate assertions drift")
        require(
            source_entry["gate_media_sha256_path"] == gate_evidence["media_sha256_path"],
            f"{config_entry['section_id']} gate media path drift",
        )
    timeline = manifest["timeline"]
    require(timeline["duration_s"] == config["render"]["expected_duration_s"], "combined timeline duration drift")
    require(
        [(item["section_id"], item["start_s"], item["end_s"]) for item in timeline["sections"]]
        == [
            ("storm", 3.0, 15.0),
            ("heat", 15.0, 25.0),
            ("snow", 25.0, 35.0),
            ("fade", 35.0, 45.0),
            ("corridor", 45.0, 57.0),
        ],
        "combined section timeline drift",
    )
    require(
        manifest["storyboard"]
        == {
            "weather_count": 4,
            "nodes_per_weather": [6, 6, 6, 6],
            "total_node_count": 24,
            "reference_frames_are_runtime_captures": False,
            "reference_frames_are_style_only": True,
        },
        "storyboard summary drift",
    )
    require(manifest["asset_status"] == {"usage": "TEMP_REFERENCE_ONLY", "formal_use_allowed": False}, "asset status drift")
    require(
        manifest["gate_status"] in {"MACHINE_VALIDATION_PENDING", "MACHINE_PASS_READY_FOR_INDEPENDENT_REVIEW"},
        "candidate gate status drift",
    )

    output_root = REPO / config["outputs"]["artifact_root"]
    require(output_root.resolve() == EXPECTED_OUTPUT_ROOT.resolve(), "candidate output path drift")
    entry = manifest["outputs"]["combined_video"]
    video = output_root / entry["file"]
    require(video.resolve() == (EXPECTED_OUTPUT_ROOT / "V-04-H3-combined-review-candidate-v1.mp4").resolve(), "combined video path drift")
    require(video.is_file(), "combined video missing")
    require(video.stat().st_size == entry["size_bytes"] and sha256(video) == entry["sha256"], "combined video drift")
    require([path.name for path in output_root.iterdir()] == [config["outputs"]["combined_video"]], "artifact root contains unexpected files")
    probe = entry["ffprobe"]
    video_stream = stream(probe, "video")
    audio_stream = stream(probe, "audio")
    require((video_stream.get("width"), video_stream.get("height")) == (3840, 1200), "combined frame size drift")
    require(video_stream.get("codec_name") == "h264" and video_stream.get("pix_fmt") == "yuv420p", "combined video codec drift")
    require(video_stream.get("avg_frame_rate") == "30/1", "combined frame rate drift")
    require(int(video_stream.get("nb_frames", 0)) == 1860, "combined frame count drift")
    require(audio_stream.get("codec_name") == "aac", "combined audio codec drift")
    require(audio_stream.get("sample_rate") == "48000" and audio_stream.get("channels") == 2, "combined audio format drift")
    duration = float(probe["format"]["duration"])
    require(abs(duration - 62.0) <= 0.05 and duration <= float(config["render"]["maximum_duration_s"]), "combined duration drift")
    validate_image(manifest["outputs"]["combined_keyframes"], EXPECTED_KEYFRAME_PATH, (3840, 640))
    validate_image(manifest["outputs"]["storyboard_sheet"], EXPECTED_STORYBOARD_SHEET_PATH, (3840, 1600))
    return video


def write_promoted_manifest_and_report(config: dict[str, object], manifest: dict[str, object]) -> None:
    manifest["gate_status"] = "MACHINE_PASS_READY_FOR_INDEPENDENT_REVIEW"
    manifest["next_if_pass"] = "INDEPENDENT_AGENT_REVIEW_THEN_TEAM_DIRECTOR_H3_CONFIRMATION"
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "schema_version": "1.0",
        "task_id": "V-04",
        "gate_id": "H3_COMBINED_REVIEW",
        "candidate_id": config["candidate_id"],
        "validated_at": config["render_requested_at"],
        "result": "PASS",
        "candidate_manifest_sha256": sha256(MANIFEST_PATH),
        "checks": {
            "five_source_hashes_and_manifests": "PASS",
            "five_source_gate_records_bound": "PASS",
            "review_order_not_runtime_sequence": "PASS",
            "duration_62s_under_120s": "PASS",
            "video_audio_format_and_decode": "PASS",
            "four_weather_six_node_contract": "PASS",
            "f01_boundary_evidence_semantics": "PASS",
            "f05_all_weather_demo_cycle_gate": "PASS",
            "python_authority_and_no_participant_input": "PASS",
            "condition_parity_and_shared_transition": "PASS",
            "generated_path_allowlist": "PASS",
            "style_reference_sheet_not_runtime_capture": "PASS",
            "temporary_asset_boundary": "PASS"
        },
        "gate_status": "MACHINE_PASS_READY_FOR_INDEPENDENT_REVIEW",
        "next_gate": "INDEPENDENT_AGENT_REVIEW_THEN_TEAM_DIRECTOR_H3_CONFIRMATION",
        "evidence_boundary": "Machine checks establish the design package structure and media integrity only; Unity runtime, build, licensed production assets and live device chain remain unverified."
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    require((REPO / config["outputs"]["artifact_root"]).resolve() == EXPECTED_OUTPUT_ROOT.resolve(), "candidate output path drift")
    require((HERE / config["outputs"]["combined_keyframes"]).resolve() == EXPECTED_KEYFRAME_PATH.resolve(), "keyframe output path drift")
    require((HERE / config["outputs"]["storyboard_sheet"]).resolve() == EXPECTED_STORYBOARD_SHEET_PATH.resolve(), "storyboard output path drift")
    require(MANIFEST_PATH.resolve().parent == HERE.resolve(), "manifest output path drift")
    require(REPORT_PATH.resolve().parent == HERE.resolve(), "report output path drift")
    validate_storyboard(config, storyboard)
    video = validate_manifest(config, manifest)
    ffmpeg = Path(lock["ffmpeg"]["ffmpeg_executable"])
    require(ffmpeg.is_file(), "locked FFmpeg executable missing")
    validate_media_health(ffmpeg, video)
    if args.write_report:
        write_promoted_manifest_and_report(config, manifest)
    print(
        "PASS: V-04 H3 combined review machine gate; five bound inputs, 62s media, "
        "four weather x six nodes, source gates, F-01/F-05 bindings, output paths and asset status verified"
    )


if __name__ == "__main__":
    main()
