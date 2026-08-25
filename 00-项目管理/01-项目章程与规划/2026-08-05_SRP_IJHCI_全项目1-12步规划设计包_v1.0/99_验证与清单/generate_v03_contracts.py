from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
BASE = (
    ROOT
    / "00-项目管理"
    / "01-项目章程与规划"
    / "2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0"
    / "20_产品与场景设计"
    / "V-03_四层视听映射与资产来源基线"
)
UNITY_PROJECT = ROOT / "02-技术研发" / "04-Unity视觉" / "SRP-Weather-Visual"
UNITY_MANIFEST = UNITY_PROJECT / "Packages" / "manifest.json"
G02_ASSET_LEDGER = UNITY_PROJECT / "Governance" / "asset_license_ledger.json"

ASSET_REQUIRED_FIELDS = (
    "asset_id",
    "category",
    "scene",
    "layer_role",
    "author_source",
    "license",
    "ledger_group",
    "status",
    "formal_use_allowed",
    "replacement_plan",
    "owner",
    "deadline",
    "hash_or_version",
    "unity_import_plan",
)
ASSET_REQUIRED_CATEGORIES = (
    "IMAGE",
    "ANIMATION",
    "FONT",
    "AUDIO",
    "SHADER",
    "PLUGIN",
    "DIRECT_PACKAGE",
)


WEATHERS = {
    "storm": {
        "r01_module_id": "storm",
        "phase_slots": ["INHALE", "HOLD_1", "EXHALE", "HOLD_2"],
        "runtime_binding": "F-05_V2_2_REQUIRED",
        "target": "FORWARD_RAIN_CURTAIN_GATE",
        "actual": "NEAR_AIRFLOW_AND_RAIN_TRACE",
        "recovery": "RAIN_INTENSITY_AND_PATH_VISIBILITY",
        "background": "STORM_PASS_NON_PERIODIC_ENVIRONMENT",
        "audio": "AUD_STORM_AMBIENT_MASTER",
    },
    "heat": {
        "r01_module_id": "scorching",
        "phase_slots": ["INHALE", "EXHALE"],
        "runtime_binding": "V2_1_COARSE_PHASE_DIRECT",
        "target": "FORWARD_COOL_AIR_CORRIDOR",
        "actual": "NEAR_COOL_AIR_AND_SALT_DUST_TRACE",
        "recovery": "HEAT_HAZE_AND_DISTANCE_CLARITY",
        "background": "SALT_FLAT_NON_PERIODIC_ENVIRONMENT",
        "audio": "AUD_HEAT_AMBIENT_MASTER",
    },
    "snow": {
        "r01_module_id": "blizzard",
        "phase_slots": ["INHALE", "EXHALE"],
        "runtime_binding": "V2_1_COARSE_PHASE_DIRECT",
        "target": "FORWARD_DETERMINISTIC_POWDER_SNOW_GROUP",
        "actual": "NEAR_POWDER_SNOW_TRACE",
        "recovery": "SNOW_MIST_AND_TREE_LINE_CLARITY",
        "background": "SNOW_FOREST_REPLAYABLE_NON_PERIODIC_ENVIRONMENT",
        "audio": "AUD_SNOW_AMBIENT_MASTER",
    },
    "fade": {
        "r01_module_id": "fading",
        "phase_slots": ["INHALE_1", "INHALE_2", "EXHALE_1"],
        "runtime_binding": "F-05_V2_2_REQUIRED",
        "target": "FORWARD_CHROMATIC_TIDE_MAIN_AND_SUPPLEMENT_FLOW",
        "actual": "NEAR_CHROMATIC_THREAD",
        "recovery": "OUTLINE_TEXTURE_AND_BASE_COLOR_COMPLETENESS",
        "background": "MIST_WETLAND_NON_PERIODIC_ENVIRONMENT",
        "audio": "AUD_FADE_AMBIENT_MASTER",
    },
}


def source_fields(weather: str, layer: str) -> list[str]:
    fields = {
        "target": ["target_phase", "target_progress"],
        "actual": ["actual_phase", "actual_progress", "actual_confidence"],
        "recovery": ["recovery_value"],
        "fallback": ["signal_quality", "fallback_state", "fallback_reason"],
        "background": [],
    }[layer]
    return fields


def carrier(weather: str, mode: str, layer: str) -> str:
    profile = WEATHERS[weather]
    if layer == "target":
        return profile["target"] if mode == "scene_native" else "ABSTRACT_OUTER_RING"
    if layer == "actual":
        return profile["actual"] if mode == "scene_native" else "ABSTRACT_INNER_RING"
    if layer == "recovery":
        return profile["recovery"]
    if layer == "fallback":
        return (
            "SCENE_ACTUAL_CARRIER_CERTAINTY_WRAPPER"
            if mode == "scene_native"
            else "ABSTRACT_INNER_RING_CERTAINTY_WRAPPER"
        )
    return profile["background"]


def build_rows() -> list[dict[str, object]]:
    semantics = {
        "target": "WHAT_IS_THE_CURRENT_TARGET_STEP_AND_PROGRESS",
        "actual": "WHAT_STEP_AND_PROGRESS_IS_CURRENTLY_ESTIMATED",
        "recovery": "HOW_IS_THE_CURRENT_MODULE_CUMULATIVE_ENVIRONMENT_CHANGING",
        "fallback": "IS_ACTUAL_INFORMATION_LOW_CERTAINTY_OR_TEMPORARILY_UNAVAILABLE",
        "background": "WHICH_WEATHER_SPACE_IS_CURRENTLY_PRESENTED",
    }
    triggers = {
        "target": "VALIDATED_TELEMETRY_FRAME",
        "actual": "VALIDATED_TELEMETRY_FRAME",
        "recovery": "VALIDATED_TELEMETRY_FRAME",
        "fallback": "QUALITY_OR_FALLBACK_CHANGE",
        "background": "SESSION_SEGMENT_AND_SCROLL_TIMELINE",
    }
    qualities = {
        "target": {
            "GOOD": "CONTINUE_TARGET",
            "DEGRADED": "CONTINUE_TARGET",
            "UNUSABLE": "OPEN_LOOP_TARGET",
            "DISCONNECTED": "FOLLOW_PYTHON_SAFE_OPEN_LOOP_OR_ABORT",
        },
        "actual": {
            "GOOD": "ACTIVE",
            "DEGRADED": "ACTIVE_LOW_CERTAINTY",
            "UNUSABLE": "STATIC_BROKEN_OUTLINE",
            "DISCONNECTED": "STATIC_BROKEN_OUTLINE",
        },
        "recovery": {
            "GOOD": "FOLLOW_PYTHON_UPDATE",
            "DEGRADED": "FOLLOW_PYTHON_CAUTION_OR_PAUSE",
            "UNUSABLE": "PAUSE_AND_LOCK_LAST_VALUE",
            "DISCONNECTED": "PAUSE_AND_LOCK_LAST_VALUE",
        },
        "fallback": {
            "GOOD": "NO_EXTRA_MARKER",
            "DEGRADED": "LOW_CERTAINTY_ON_ACTUAL_ONLY",
            "UNUSABLE": "TEMPORARILY_UNAVAILABLE_ON_ACTUAL_ONLY",
            "DISCONNECTED": "TEMPORARILY_UNAVAILABLE_ON_ACTUAL_ONLY",
        },
        "background": {
            "GOOD": "UNCHANGED",
            "DEGRADED": "UNCHANGED",
            "UNUSABLE": "UNCHANGED",
            "DISCONNECTED": "UNCHANGED",
        },
    }
    forbidden = {
        "target": ["actual", "actual_confidence", "error", "recovery", "fallback"],
        "actual": ["target", "error", "recovery"],
        "recovery": ["target", "actual", "quality_as_local_override"],
        "fallback": ["target", "recovery", "background_global_warning", "audio_warning"],
        "background": ["target", "actual", "recovery", "quality", "respiratory_period"],
    }
    evidence = {
        "target": "TARGET_FIXTURE_RENDER_RECEIPT_AND_GRAYSCALE_VIDEO",
        "actual": "DIVERGENT_ACTUAL_FIXTURE_RENDER_RECEIPT_AND_GRAYSCALE_VIDEO",
        "recovery": "BIDIRECTIONAL_RECOVERY_FIXTURE_AND_PARAMETER_LOG",
        "fallback": "QUALITY_FAULT_INJECTION_AND_VIDEO",
        "background": "BACKGROUND_HASH_SCROLL_LOG_AND_PERIOD_LEAKAGE_REVIEW",
    }
    rows: list[dict[str, object]] = []
    for weather in WEATHERS:
        for mode in ("scene_native", "abstract_pacer"):
            for layer in ("target", "actual", "recovery", "fallback", "background"):
                rows.append(
                    {
                        "technical_id": weather,
                        "cue_mode": mode,
                        "layer": layer,
                        "source_fields": source_fields(weather, layer),
                        "design_phase_slots": (
                            WEATHERS[weather]["phase_slots"]
                            if layer in {"target", "actual"}
                            else []
                        ),
                        "runtime_slot_binding": (
                            WEATHERS[weather]["runtime_binding"]
                            if layer in {"target", "actual"}
                            else "NOT_APPLICABLE"
                        ),
                        "semantic_question": semantics[layer],
                        "visual_carrier": carrier(weather, mode, layer),
                        "audio_role": WEATHERS[weather]["audio"] if layer == "background" else "NONE",
                        "update_trigger": triggers[layer],
                        "quality_behavior": qualities[layer],
                        "forbidden_coupling": forbidden[layer],
                        "evidence_hook": evidence[layer],
                    }
                )
    return rows


def mapping_contract() -> dict[str, object]:
    return {
        "schema_id": "V03_DESIGN_SEMANTICS_1_0",
        "version": "1.0",
        "status": "CANDIDATE_READY_FOR_REVIEW",
        "row_count": 40,
        "technical_ids": list(WEATHERS),
        "cue_modes": ["scene_native", "abstract_pacer"],
        "layers": ["target", "actual", "recovery", "fallback", "background"],
        "r01_module_id_map": {
            weather: profile["r01_module_id"] for weather, profile in WEATHERS.items()
        },
        "weather_profiles": WEATHERS,
        "runtime_binding_boundary": {
            "design_semantics_complete_before_f05": True,
            "storm_and_fade_runtime_binding_owner": "F-05",
            "missing_v22_binding_blocks_v03_design_completion": False,
            "missing_v22_binding_blocks_related_runtime_implementation": True,
        },
        "confidence_fallback_composition": {
            "available_rule": (
                "VISIBLE_CERTAINTY_EQUALS_MIN_OF_ACTUAL_CONFIDENCE_ENVELOPE_"
                "AND_FALLBACK_STATE_CAP"
            ),
            "good_cap": 1.0,
            "degraded_cap_candidate": 0.70,
            "unusable_or_disconnected_rule": (
                "FREEZE_LAST_VALID_GEOMETRY_AND_APPLY_STATIC_BROKEN_OUTLINE"
            ),
            "fallback_layer_reads_actual_confidence": False,
            "exact_cap_freeze_gate": "U-03_DEGRADED_VISIBILITY_EVIDENCE",
        },
        "rows": build_rows(),
    }


def mapping_schema() -> dict[str, object]:
    contract = mapping_contract()
    allowed_source_fields = [
        "target_phase",
        "target_progress",
        "actual_phase",
        "actual_progress",
        "actual_confidence",
        "recovery_value",
        "signal_quality",
        "fallback_state",
        "fallback_reason",
    ]
    allowed_slots = [
        "INHALE",
        "HOLD_1",
        "EXHALE",
        "HOLD_2",
        "INHALE_1",
        "INHALE_2",
        "EXHALE_1",
    ]
    row_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "technical_id",
            "cue_mode",
            "layer",
            "source_fields",
            "design_phase_slots",
            "runtime_slot_binding",
            "semantic_question",
            "visual_carrier",
            "audio_role",
            "update_trigger",
            "quality_behavior",
            "forbidden_coupling",
            "evidence_hook",
        ],
        "properties": {
            "technical_id": {"enum": ["storm", "heat", "snow", "fade"]},
            "cue_mode": {"enum": ["scene_native", "abstract_pacer"]},
            "layer": {
                "enum": ["target", "actual", "recovery", "fallback", "background"]
            },
            "source_fields": {
                "type": "array",
                "uniqueItems": True,
                "items": {"enum": allowed_source_fields},
            },
            "design_phase_slots": {
                "type": "array",
                "uniqueItems": True,
                "items": {"enum": allowed_slots},
            },
            "runtime_slot_binding": {
                "enum": [
                    "F-05_V2_2_REQUIRED",
                    "V2_1_COARSE_PHASE_DIRECT",
                    "NOT_APPLICABLE",
                ]
            },
            "semantic_question": {"type": "string", "minLength": 1},
            "visual_carrier": {"type": "string", "minLength": 1},
            "audio_role": {"type": "string", "minLength": 1},
            "update_trigger": {
                "enum": [
                    "VALIDATED_TELEMETRY_FRAME",
                    "QUALITY_OR_FALLBACK_CHANGE",
                    "SESSION_SEGMENT_AND_SCROLL_TIMELINE",
                ]
            },
            "quality_behavior": {
                "type": "object",
                "additionalProperties": False,
                "required": ["GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED"],
                "properties": {
                    state: {"type": "string", "minLength": 1}
                    for state in ("GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED")
                },
            },
            "forbidden_coupling": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
            "evidence_hook": {"type": "string", "minLength": 1},
        },
        "allOf": [
            {
                "if": {"properties": {"layer": {"const": "background"}}},
                "then": {
                    "properties": {
                        "source_fields": {"maxItems": 0},
                        "audio_role": {"pattern": "^AUD_"},
                        "design_phase_slots": {"maxItems": 0},
                        "runtime_slot_binding": {"const": "NOT_APPLICABLE"},
                    }
                },
                "else": {
                    "properties": {
                        "source_fields": {"minItems": 1},
                        "audio_role": {"const": "NONE"},
                    }
                },
            },
            {
                "if": {
                    "properties": {"layer": {"enum": ["target", "actual"]}}
                },
                "then": {
                    "properties": {
                        "design_phase_slots": {"minItems": 2},
                        "runtime_slot_binding": {
                            "enum": [
                                "F-05_V2_2_REQUIRED",
                                "V2_1_COARSE_PHASE_DIRECT",
                            ]
                        },
                    }
                },
                "else": {
                    "properties": {
                        "design_phase_slots": {"maxItems": 0},
                        "runtime_slot_binding": {"const": "NOT_APPLICABLE"},
                    }
                },
            },
        ],
    }
    representative_rows = {
        layer: next(row for row in build_rows() if row["layer"] == layer)
        for layer in ("target", "actual", "recovery", "fallback", "background")
    }
    for layer, row in representative_rows.items():
        row_schema["allOf"].append(
            {
                "if": {"properties": {"layer": {"const": layer}}},
                "then": {
                    "properties": {
                        "source_fields": {"const": row["source_fields"]},
                        "quality_behavior": {"const": row["quality_behavior"]},
                    }
                },
            }
        )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:srp:v03:design-semantics:1.0",
        "title": "V-03 design semantics mapping contract",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_id",
            "version",
            "status",
            "row_count",
            "technical_ids",
            "cue_modes",
            "layers",
            "r01_module_id_map",
            "weather_profiles",
            "runtime_binding_boundary",
            "confidence_fallback_composition",
            "rows",
        ],
        "properties": {
            "schema_id": {"const": "V03_DESIGN_SEMANTICS_1_0"},
            "version": {"const": "1.0"},
            "status": {"const": "CANDIDATE_READY_FOR_REVIEW"},
            "row_count": {"const": 40},
            "technical_ids": {
                "const": ["storm", "heat", "snow", "fade"]
            },
            "cue_modes": {"const": ["scene_native", "abstract_pacer"]},
            "layers": {
                "const": ["target", "actual", "recovery", "fallback", "background"]
            },
            "r01_module_id_map": {
                "const": {
                    "storm": "storm",
                    "heat": "scorching",
                    "snow": "blizzard",
                    "fade": "fading",
                }
            },
            "weather_profiles": {"const": contract["weather_profiles"]},
            "runtime_binding_boundary": {
                "const": contract["runtime_binding_boundary"]
            },
            "confidence_fallback_composition": {
                "const": contract["confidence_fallback_composition"]
            },
            "rows": {
                "type": "array",
                "minItems": 40,
                "maxItems": 40,
                "items": row_schema,
            },
        },
    }


def risk_contract() -> dict[str, object]:
    dimensions = [
        "four_layer_conflict",
        "phase_discriminability",
        "implementation",
        "performance",
        "fallback_readability",
        "asset_provenance",
        "condition_matching",
    ]
    scores = {
        "A": {
            "storm": [3, 4, 3, 3, 3, 3, 3],
            "heat": [2, 2, 2, 2, 2, 2, 2],
            "snow": [3, 2, 4, 4, 3, 3, 3],
            "fade": [4, 4, 4, 3, 4, 4, 4],
        },
        "B": {
            "storm": [4, 4, 3, 4, 4, 3, 4],
            "heat": [2, 1, 2, 3, 2, 3, 2],
            "snow": [4, 2, 4, 4, 4, 3, 4],
            "fade": [4, 4, 4, 3, 4, 3, 4],
        },
    }
    reasons = {
        "A": {
            "storm": [
                "Rain materials overlap across target, actual, recovery and fallback.",
                "Two hold slots require explicit identity and stable boundaries.",
                "Gate deformation, near trace and rain masks require coordinated adapters.",
                "Rain, mist and transparent traces create moderate overdraw pressure.",
                "Broken near rain traces can blend into the ambient rain field.",
                "Scroll, masks, effects and audio all require new provenance records.",
                "Removing gate motion in abstract mode can create attention imbalance.",
            ],
            "heat": [
                "Cool-flow cues are spatially separable from cumulative haze.",
                "Two directional phases have a simple identity boundary.",
                "Fixed paths and bounded haze are relatively direct to implement.",
                "Full-screen refraction creates moderate rendering pressure.",
                "Near cool-flow traces remain spatially locatable when softened.",
                "All production assets still require provenance records.",
                "Travel length and salience still require paired calibration.",
            ],
            "snow": [
                "Ambient, target and actual snow use similar visual materials.",
                "Mirrored inhale and exhale are directionally distinct.",
                "Deterministic particles and replay require substantial implementation work.",
                "Several snow and mist layers create high overdraw pressure.",
                "Broken actual snow traces may blend into ambient snowfall.",
                "Forest strips, particles, masks and audio need provenance records.",
                "Removing phase snow in abstract mode changes motion and object counts.",
            ],
            "fade": [
                "Current tide and cumulative color-texture state share visual materials.",
                "Two inhale slots and one long exhale require explicit step identity.",
                "Non-resetting double inhale and deterministic masks are complex.",
                "Water mist and masks create moderate transparent-layer pressure.",
                "Low-saturation broken actual threads can resemble cumulative low values.",
                "Wetland strips and multiple semantic masks need detailed provenance.",
                "Double tide and double ring must match while remaining grayscale-readable.",
            ],
        },
        "B": {
            "storm": [
                "Rain visual material is shared by four semantic roles.",
                "Two holds depend on explicit step identity.",
                "Gate, airflow and weather masks need coordinated control.",
                "Rain, mist, airflow and scroll create high overdraw risk.",
                "Broken rain traces can be mistaken for ambient rain.",
                "All weather assets remain pending provenance closure.",
                "Abstract mode removes a salient gate motion channel.",
            ],
            "heat": [
                "Cool-flow and haze roles are comparatively separable.",
                "Only inhale and exhale need to be distinguished.",
                "Fixed spline and haze parameters are relatively direct.",
                "Full-screen refraction can still affect performance.",
                "Near cool-flow remains locatable under degradation.",
                "All assets remain pending provenance closure.",
                "Travel and salience need ordinary paired calibration.",
            ],
            "snow": [
                "Ambient, target, actual and cumulative snow materials overlap.",
                "Mirrored direction provides a clear two-phase distinction.",
                "Deterministic particles, pause and replay are complex.",
                "Multiple particle and mist layers create high overdraw.",
                "Broken actual snow can resemble ambient snowfall.",
                "All assets remain pending provenance closure.",
                "Abstract mode changes active particle count and motion energy.",
            ],
            "fade": [
                "Tide, thread and cumulative color-texture materials overlap.",
                "Two inhales require explicit v2.2 step identity.",
                "Non-resetting double inhale and fixed flow paths are complex.",
                "Transparent wetland masks create moderate pressure.",
                "Low-saturation broken threads can blend into cumulative state.",
                "All assets remain pending provenance closure.",
                "Double tide and double ring need paired grayscale calibration.",
            ],
        },
    }
    scorers: dict[str, object] = {}
    for scorer, weather_scores in scores.items():
        scorers[scorer] = {
            weather: {
                "scores": dict(zip(dimensions, values, strict=True)),
                "reasons": dict(zip(dimensions, reasons[scorer][weather], strict=True)),
                "total": sum(values),
            }
            for weather, values in weather_scores.items()
        }
    return {
        "version": "1.0",
        "status": "DUAL_SCORING_COMPLETE_DIFFERENCES_RESOLVED",
        "dimensions": dimensions,
        "range": [0, 4],
        "weights": "EQUAL",
        "scorers": scorers,
        "difference_audit": {
            "any_dimension_gap_gte_2": False,
            "scorer_a_top_set": ["fade"],
            "scorer_b_top_set": ["storm", "fade"],
            "top_set_difference_resolved": True,
        },
        "upstream_contract_gap_definition": {
            "step_1": "COUNT_UNRESOLVED_UPSTREAM_GATES_BLOCKING_THE_SLICE",
            "step_2": (
                "IF_TIED_COMPARE_SEVERITY_SCHEMA_OR_FIELD_IDENTITY_THEN_"
                "TIMING_OR_CONFIG_THEN_ASSET_OR_ENGINE"
            ),
            "step_3": "IF_STILL_TIED_COMPARE_NUMBER_OF_BLOCKED_DOWNSTREAM_CONSUMERS",
        },
        "resolution": (
            "FADE_WINS_OVER_STORM_BECAUSE_BOTH_REQUIRE_F05_STEP_IDENTITY_"
            "BUT_FADE_ALSO_LACKS_FROZEN_STEP_TIMING_AND_BOUNDARY_CONFIG"
        ),
        "selected_u03_weather": "fade",
        "selection_status": "FROZEN_FOR_V03_DESIGN_HANDOFF",
    }


def parameter_contract() -> dict[str, object]:
    return {
        "version": "1.0",
        "status": "CANDIDATE_READY_FOR_REVIEW",
        "common": {
            "phase_interpolation_ms": [100, 250],
            "recovery_low_pass_s": [2, 5],
            "actual_degraded_opacity": [0.45, 0.70],
            "actual_unavailable_opacity": [0.25, 0.45],
            "actual_degraded_continuity": [0.45, 0.75],
            "actual_edge_softening_px_1080p": [1, 3],
            "abstract_outer_diameter_short_edge": [0.18, 0.24],
            "abstract_inner_outer_radius_ratio": [0.62, 0.76],
            "abstract_line_width_short_edge": [0.004, 0.008],
            "horizon_y": [0.56, 0.62],
            "scroll_speed_viewport_per_s": [0.015, 0.025],
            "scroll_speed_default": 0.02,
            "parallax": {"far": [0.30, 0.45], "mid": [0.60, 0.80], "near": 1.0},
            "scroll_effective_coverage_min": 6.75,
            "segment_raw_width_max": 2.0,
            "segment_overlap": [0.10, 0.15],
            "ambient_integrated_loudness_lufs_i": [-24, -20],
            "ambient_true_peak_max_dbtp": -3,
            "scene_corridor_crossfade_s": [2, 4],
            "ambient_loop_minimum_s": 60,
        },
        "safe_areas": {
            "target": {"x": [0.55, 0.85], "y": [0.34, 0.72]},
            "actual": {"x": [0.20, 0.45], "y": [0.18, 0.52]},
            "abstract_center": [0.50, 0.50],
        },
        "recovery_endpoints": {
            "storm": {
                "rain_multiplier": {"low": [1.0, 1.0], "high": [0.65, 0.80]},
                "visibility": {"low": [0.45, 0.60], "high": [0.70, 0.85]},
            },
            "heat": {
                "haze_multiplier": {"low": [1.0, 1.0], "high": [0.55, 0.75]},
                "clarity": {"low": [0.45, 0.60], "high": [0.70, 0.85]},
            },
            "snow": {
                "mist_multiplier": {"low": [1.0, 1.0], "high": [0.60, 0.80]},
                "tree_line_clarity": {"low": [0.45, 0.60], "high": [0.70, 0.85]},
            },
            "fade": {
                "outline_texture_base_color_completeness": {
                    "low": [0.35, 0.50],
                    "high": [0.65, 0.80],
                }
            },
        },
        "shared_rules": {
            "recovery_curve": "LINEAR_0_TO_1",
            "same_between_cue_modes": True,
            "no_forced_full_endpoint": True,
            "weather_identity_retained_at_high_value": True,
            "exact_values_require_runtime_evidence": True,
        },
    }


def asset_entry(
    asset_id: str,
    category: str,
    scene: str,
    layer_role: str,
    owner: str,
    deadline: str,
    replacement_plan: str,
    unity_import_plan: str,
    *,
    author_source: str = "SRP_PROJECT_TEAM_OR_APPROVED_SOURCE_PENDING_INSTANCE",
    license_name: str = "PENDING_ASSET_INSTANCE_RIGHTS_EVIDENCE",
    ledger_group: str = "PENDING_G02_INSTANCE_REGISTRATION",
    status: str = "PLANNED_PENDING_INSTANCE_PROVENANCE",
    hash_or_version: str = "PENDING_FINAL_SHA256",
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "category": category,
        "scene": scene,
        "layer_role": layer_role,
        "author_source": author_source,
        "license": license_name,
        "ledger_group": ledger_group,
        "status": status,
        "formal_use_allowed": False,
        "replacement_plan": replacement_plan,
        "owner": owner,
        "deadline": deadline,
        "hash_or_version": hash_or_version,
        "unity_import_plan": unity_import_plan,
    }


def design_asset_entries() -> list[dict[str, object]]:
    entries = [
        asset_entry(
            "IMG_COMMON_CORRIDOR",
            "IMAGE",
            "common_corridor",
            "SKY_FAR_MID_GROUND_FOREGROUND",
            "Unity visual lead",
            "BEFORE_V05_GREYBOX",
            "Create project-owned layered corridor art or replace with a G-02-cleared equivalent.",
            "MULTILAYER_SPRITES_SHARED_CANVAS_NO_AUTO_CROP",
        ),
        asset_entry(
            "IMG_STORM_SCROLL",
            "IMAGE",
            "storm",
            "SKY_FAR_MID_GROUND_FOREGROUND_EFFECT_MASK",
            "Unity visual lead",
            "BEFORE_U03_ASSET_IMPORT",
            "Generate and manually rebuild the storm strip set, then register every exported file in G-02.",
            "DETERMINISTIC_SEGMENTED_SCROLL_SHARED_ORIGIN",
        ),
        asset_entry(
            "IMG_HEAT_SCROLL",
            "IMAGE",
            "heat",
            "SKY_FAR_MID_GROUND_FOREGROUND_EFFECT_MASK",
            "Unity visual lead",
            "BEFORE_U04_ASSET_IMPORT",
            "Generate and manually rebuild the heat strip set, then register every exported file in G-02.",
            "DETERMINISTIC_SEGMENTED_SCROLL_SHARED_ORIGIN",
        ),
        asset_entry(
            "IMG_SNOW_SCROLL",
            "IMAGE",
            "snow",
            "SKY_FAR_MID_GROUND_FOREGROUND_EFFECT_MASK",
            "Unity visual lead",
            "BEFORE_U05_ASSET_IMPORT",
            "Generate and manually rebuild the snow strip set, then register every exported file in G-02.",
            "DETERMINISTIC_SEGMENTED_SCROLL_SHARED_ORIGIN",
        ),
        asset_entry(
            "IMG_FADE_SCROLL",
            "IMAGE",
            "fade",
            "SKY_FAR_MID_GROUND_FOREGROUND_EFFECT_MASK",
            "Unity visual lead",
            "BEFORE_U03_ASSET_IMPORT",
            "Generate and manually rebuild the fade strip set, then register every exported file in G-02.",
            "DETERMINISTIC_SEGMENTED_SCROLL_SHARED_ORIGIN",
        ),
        asset_entry(
            "ANIM_COMMON_SCROLL_CAMERA",
            "ANIMATION",
            "common",
            "CAMERA_SCROLL_PARALLAX_AND_PAUSE",
            "Unity technical lead",
            "BEFORE_V05_GREYBOX",
            "Author deterministic project-owned animation data; reject imported animation with unknown provenance.",
            "TIMELINE_OR_SCRIPTED_CURVE_WITH_FIXED_TIME_AUTHORITY",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "ANIM_STORM_SEMANTIC",
            "ANIMATION",
            "storm",
            "TARGET_ACTUAL_RECOVERY_FALLBACK",
            "Unity visual lead",
            "BEFORE_U03_SLICE_REVIEW",
            "Author project-owned semantic animation from the V-03 contract and replace any legacy shield motion.",
            "SCENE_ADAPTER_DRIVEN_NO_BAKED_INPUT_VALUES",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "ANIM_HEAT_SEMANTIC",
            "ANIMATION",
            "heat",
            "TARGET_ACTUAL_RECOVERY_FALLBACK",
            "Unity visual lead",
            "BEFORE_U04_DONE",
            "Author project-owned semantic animation from the V-03 contract.",
            "SCENE_ADAPTER_DRIVEN_NO_BAKED_INPUT_VALUES",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "ANIM_SNOW_SEMANTIC",
            "ANIMATION",
            "snow",
            "TARGET_ACTUAL_RECOVERY_FALLBACK",
            "Unity visual lead",
            "BEFORE_U05_DONE",
            "Author project-owned deterministic snow trajectories and semantic animation.",
            "FIXED_TRAJECTORY_SCENE_ADAPTER_DRIVEN",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "ANIM_FADE_SEMANTIC",
            "ANIMATION",
            "fade",
            "TARGET_ACTUAL_RECOVERY_FALLBACK",
            "Unity visual lead",
            "BEFORE_U03_SLICE_REVIEW",
            "Author project-owned fixed-spline semantic animation from the V-03 contract.",
            "FIXED_SPLINE_SCENE_ADAPTER_DRIVEN",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "FONT_PARTICIPANT_UI",
            "FONT",
            "common",
            "PARTICIPANT_VISIBLE_SYSTEM_TEXT_ONLY",
            "Unity visual lead",
            "BEFORE_V05_GREYBOX",
            "Select an OFL or project-owned font, archive the license, or remove participant-visible text.",
            "TMP_FONT_ASSET_WITH_LOCKED_SOURCE_HASH_AND_FALLBACKS",
            author_source="PENDING_CLEARED_FONT_SELECTION",
            license_name="PENDING_OFL_OR_PROJECT_ORIGINAL_EVIDENCE",
            status="REPLACE_PENDING_CLEARED_FONT_SELECTION",
        ),
        asset_entry(
            "AUD_COMMON_CORRIDOR_MASTER",
            "AUDIO",
            "common_corridor",
            "NON_RHYTHMIC_AMBIENT_MASTER",
            "Audio design lead",
            "BEFORE_V04_SOUND_REHEARSAL",
            "Create a project-owned master or replace it with a G-02-cleared recording.",
            "LOCKED_AUDIOCLIP_HASH_AND_AUDIO_PROFILE",
        ),
        asset_entry(
            "AUD_STORM_AMBIENT_MASTER",
            "AUDIO",
            "storm",
            "NON_RHYTHMIC_AMBIENT_MASTER",
            "Audio design lead",
            "BEFORE_V04_SOUND_REHEARSAL",
            "Create a project-owned storm master or replace it with a G-02-cleared recording.",
            "LOCKED_AUDIOCLIP_HASH_AND_AUDIO_PROFILE",
        ),
        asset_entry(
            "AUD_HEAT_AMBIENT_MASTER",
            "AUDIO",
            "heat",
            "NON_RHYTHMIC_AMBIENT_MASTER",
            "Audio design lead",
            "BEFORE_V04_SOUND_REHEARSAL",
            "Create a project-owned heat master or replace it with a G-02-cleared recording.",
            "LOCKED_AUDIOCLIP_HASH_AND_AUDIO_PROFILE",
        ),
        asset_entry(
            "AUD_SNOW_AMBIENT_MASTER",
            "AUDIO",
            "snow",
            "NON_RHYTHMIC_AMBIENT_MASTER",
            "Audio design lead",
            "BEFORE_V04_SOUND_REHEARSAL",
            "Create a project-owned snow master or replace it with a G-02-cleared recording.",
            "LOCKED_AUDIOCLIP_HASH_AND_AUDIO_PROFILE",
        ),
        asset_entry(
            "AUD_FADE_AMBIENT_MASTER",
            "AUDIO",
            "fade",
            "NON_RHYTHMIC_AMBIENT_MASTER",
            "Audio design lead",
            "BEFORE_V04_SOUND_REHEARSAL",
            "Create a project-owned fade master or replace it with a G-02-cleared recording.",
            "LOCKED_AUDIOCLIP_HASH_AND_AUDIO_PROFILE",
        ),
        asset_entry(
            "SHADER_COMMON_URP_2D",
            "SHADER",
            "common",
            "LAYER_COMPOSITING_AND_CERTAINTY_WRAPPER",
            "Unity technical lead",
            "BEFORE_U02_DONE",
            "Author project-owned Shader Graph assets or use only locked Unity URP shader sources.",
            "URP_2D_SHADER_GRAPH_WITH_MATERIAL_HASH",
            author_source="SRP_PROJECT_TEAM_OR_LOCKED_UNITY_URP_SOURCE",
            license_name="PROJECT_ORIGINAL_OR_UNITY_PACKAGE_NOTICE",
            ledger_group="PENDING_G02_INSTANCE_OR_UNITY_OFFICIAL_PACKAGES",
            status="PLANNED_PENDING_SHADER_INSTANCE",
        ),
        asset_entry(
            "SHADER_WEATHER_EFFECTS",
            "SHADER",
            "all_weather",
            "RAIN_HEAT_SNOW_FADE_EFFECTS",
            "Unity technical lead",
            "BEFORE_U03_SLICE_REVIEW",
            "Author project-owned weather effects and reject unknown downloaded shader code.",
            "URP_2D_SHADER_GRAPH_SEPARATE_FROM_RESEARCH_SEMANTICS",
            author_source="SRP_PROJECT_TEAM",
            license_name="PROJECT_ORIGINAL_AFTER_AUTHORSHIP_RECORD",
            status="PLANNED_PROJECT_ORIGINAL",
        ),
        asset_entry(
            "PLUGIN_UNITY_MCP_EDITOR",
            "PLUGIN",
            "editor_only",
            "EDITOR_AUTOMATION",
            "Unity technical lead",
            "BEFORE_F03_DONE",
            "Prove editor-only exclusion from the participant build or remove the package.",
            "EDITOR_ONLY_NO_PLAYER_ASSEMBLY",
            author_source="CoplayDev",
            license_name="MIT",
            ledger_group="coplaydev-unity-mcp",
            status="EDITOR_ONLY_PENDING_PLAYER_EXCLUSION_PROOF",
            hash_or_version="78ee5418415953b79c358bfe6355fcc3fde7912b",
        ),
        asset_entry(
            "PLUGIN_KLAK_SPOUT_LEGACY",
            "PLUGIN",
            "legacy_only",
            "LEGACY_SPOUT_TRANSPORT",
            "Unity technical lead",
            "BEFORE_F03_DONE",
            "Remove KlakSpout from the target package manifest and player build.",
            "EXCLUDE_AND_REMOVE_FROM_TARGET_ARCHITECTURE",
            author_source="Keijiro Takahashi and contributors",
            license_name="Unlicense",
            ledger_group="klak-spout",
            status="REPLACE_REMOVE_FROM_TARGET_ARCHITECTURE",
            hash_or_version="849e7bca3c167839ed697796153e1749acf0c53f",
        ),
        asset_entry(
            "PLUGIN_ROSLYN_BINARIES_LEGACY",
            "PLUGIN",
            "legacy_only",
            "LEGACY_EDITOR_BINARY",
            "Unity technical lead",
            "BEFORE_F03_DONE",
            "Remove Assets/Plugins/Roslyn or reacquire pinned binaries with exact evidence.",
            "EXCLUDE_FROM_PLAYER_AND_REPLACE_OR_REMOVE",
            author_source="DOTNET_FOUNDATION_EXACT_BINARY_SOURCE_PENDING",
            license_name="PENDING_EXACT_BINARY_PROVENANCE",
            ledger_group="roslyn-binaries-unresolved",
            status="REPLACE",
            hash_or_version="PENDING_EXACT_BINARY_SHA256",
        ),
    ]
    return entries


def direct_package_entries() -> list[dict[str, object]]:
    manifest = json.loads(UNITY_MANIFEST.read_text(encoding="utf-8"))
    entries: list[dict[str, object]] = []
    for package_id, version in sorted(manifest["dependencies"].items()):
        if package_id == "com.coplaydev.unity-mcp":
            author_source = "CoplayDev"
            license_name = "MIT"
            ledger_group = "coplaydev-unity-mcp"
            status = "EDITOR_ONLY_PENDING_PLAYER_EXCLUSION_PROOF"
            replacement_plan = "Prove editor-only exclusion from the participant build or remove the direct dependency."
            import_plan = "LOCK_COMMIT_EDITOR_ONLY_OR_REMOVE"
        elif package_id == "jp.keijiro.klak.spout":
            author_source = "Keijiro Takahashi and contributors"
            license_name = "Unlicense"
            ledger_group = "klak-spout"
            status = "REPLACE_REMOVE_FROM_TARGET_ARCHITECTURE"
            replacement_plan = "Remove this legacy direct dependency before the F-03 target baseline is signed."
            import_plan = "REMOVE_FROM_MANIFEST_AND_PACKAGES_LOCK"
        elif package_id.startswith("com.unity."):
            author_source = "Unity Technologies"
            license_name = "Unity Companion License and applicable package notices"
            ledger_group = "unity-official-packages"
            status = "G02_GROUP_CLEARED_PENDING_F03_SCOPE_FREEZE"
            replacement_plan = "F-03 must retain only packages required by the target build and archive applicable notices."
            import_plan = "LOCK_VERSION_AND_PACKAGE_NOTICE_OR_REMOVE"
        else:
            raise AssertionError(f"unclassified direct package: {package_id}")
        entries.append(
            asset_entry(
                f"PKG::{package_id}",
                "DIRECT_PACKAGE",
                "common",
                "UNITY_DIRECT_DEPENDENCY",
                "Unity technical lead",
                "BEFORE_F03_DONE",
                replacement_plan,
                import_plan,
                author_source=author_source,
                license_name=license_name,
                ledger_group=ledger_group,
                status=status,
                hash_or_version=str(version),
            )
        )
    return entries


def asset_registry() -> dict[str, object]:
    design_entries = design_asset_entries()
    package_entries = direct_package_entries()
    entries = design_entries + package_entries
    return {
        "registry_id": "SRP_V03_ASSET_SOURCE_REPLACEMENT_REGISTRY",
        "version": "1.0",
        "status": "CANDIDATE_AC3_COMPLETE_PENDING_G02_CLEARANCE",
        "formal_release_rule": (
            "NO_ENTRY_IS_FORMALLY_USABLE_UNTIL_ITS_INSTANCE_EVIDENCE_AND_"
            "THE_G02_FORMAL_BUILD_GATE_ARE_CLEARED"
        ),
        "authorities": {
            "unity_manifest": UNITY_MANIFEST.relative_to(ROOT).as_posix(),
            "unity_manifest_sha256": hashlib.sha256(UNITY_MANIFEST.read_bytes()).hexdigest(),
            "g02_asset_ledger": G02_ASSET_LEDGER.relative_to(ROOT).as_posix(),
            "g02_asset_ledger_sha256": hashlib.sha256(G02_ASSET_LEDGER.read_bytes()).hexdigest(),
        },
        "required_categories": list(ASSET_REQUIRED_CATEGORIES),
        "required_fields": list(ASSET_REQUIRED_FIELDS),
        "design_entry_count": len(design_entries),
        "direct_package_count": len(package_entries),
        "entry_count": len(entries),
        "entries": entries,
    }


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    write_json(BASE / "V-03_四层视听映射合同_v1.0.json", mapping_contract())
    write_json(
        BASE / "V-03_四层视听映射合同_v1.0.schema.json",
        mapping_schema(),
    )
    write_json(BASE / "V-03_参数边界与锁定规则_v1.0.json", parameter_contract())
    write_json(BASE / "V-03_工程风险评分_v1.0.json", risk_contract())
    write_json(BASE / "V-03_资产来源与替换台账_v1.0.json", asset_registry())
    print(
        "generated V-03 mapping rows=40, schema, parameters, dual risk scores "
        "and asset registry"
    )


if __name__ == "__main__":
    main()
