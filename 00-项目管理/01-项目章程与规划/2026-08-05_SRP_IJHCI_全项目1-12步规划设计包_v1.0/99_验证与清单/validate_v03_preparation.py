from __future__ import annotations

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


def main() -> None:
    plan_path = BASE / "V-03_前期规划与上下游对齐_v1.0.md"
    baseline_path = BASE / "v03-planning-baseline-v1.0.json"
    readme_path = BASE / "README.md"

    for path in (plan_path, baseline_path, readme_path):
        assert path.is_file(), f"missing V-03 preparation artifact: {path}"

    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert data["status"] == "CANDIDATE_READY_FOR_SECOND_PERSON_REVIEW"
    assert data["scope"] == (
        "planning_alignment_and_detailed_design_candidates_no_runtime_evidence"
    )
    assert data["task_status_authority"] == "IN_PROGRESS"
    assert set(data["technical_ids"]) == {"storm", "heat", "snow", "fade"}
    assert set(data["cue_modes"]) == {"scene_native", "abstract_pacer"}
    assert len(data["deliverable_templates"]) == 6
    assert len(data["risk_dimensions"]) == 7

    risk_scoring = data["risk_scoring"]
    assert risk_scoring == {
        "range": [0, 4],
        "weights": "EQUAL",
        "independent_scorers": 2,
        "mandatory_resolution_dimension_gap": 2,
        "mandatory_resolution_if_top_weather_differs": True,
        "tie_break_order": [
            "upstream_contract_gap",
            "condition_matching",
            "fallback_readability",
            "performance",
        ],
        "tie_break_definitions": {
            "upstream_contract_gap": [
                "COUNT_UNRESOLVED_UPSTREAM_GATES_BLOCKING_THE_SLICE",
                (
                    "IF_TIED_COMPARE_SCHEMA_OR_FIELD_IDENTITY_THEN_TIMING_OR_"
                    "CONFIG_THEN_ASSET_OR_ENGINE"
                ),
                "IF_STILL_TIED_COMPARE_BLOCKED_DOWNSTREAM_CONSUMER_COUNT",
            ],
            "condition_matching": "COMPARE_EXISTING_CONDITION_MATCHING_DIMENSION_SCORE",
            "fallback_readability": (
                "COMPARE_EXISTING_FALLBACK_READABILITY_DIMENSION_SCORE"
            ),
            "performance": "COMPARE_EXISTING_PERFORMANCE_DIMENSION_SCORE",
        },
        "legacy_asset_or_visual_preference_affects_score": False,
    }

    fallback = data["fallback_presentation"]
    assert set(fallback["backend_states"]) == {
        "GOOD",
        "DEGRADED",
        "UNUSABLE",
        "DISCONNECTED",
    }
    assert fallback["participant_visible_classes"] == {
        "LOW_CERTAINTY": ["DEGRADED"],
        "TEMPORARILY_UNAVAILABLE": ["UNUSABLE", "DISCONNECTED"],
    }
    assert fallback["good_has_extra_marker"] is False
    assert fallback["text_or_audio_warning"] is False
    assert fallback["global_scene_warning"] is False

    recovery = data["recovery_lifecycle"]
    assert recovery == {
        "scope": "PER_MODULE",
        "demo": "NEUTRAL_BASELINE_NO_ACCUMULATION_PRESENTATION",
        "closed_loop": "FOLLOW_PYTHON_RECOVERY_VALUE_SLOWLY",
        "closed_loop_end": "LOCK_ACTUAL_VALUE_NO_FORCED_COMPLETION",
        "lock_transition": "HOLD_THEN_FADE_TO_NEUTRAL_CORRIDOR",
        "next_module": "RESET_TO_NEXT_MODULE_NEUTRAL_BASELINE",
        "previous_value_persisted_in_record_only": True,
    }

    relationship = data["target_actual_relationship"]
    assert relationship == {
        "perceptual_synchrony_allowed": True,
        "spatial_or_layer_separation_required": True,
        "snapping": False,
        "merging": False,
        "connector_or_error_arrow": False,
        "success_reward": False,
        "actual_reads_target_or_error_fields": False,
    }

    interpolation = data["phase_interpolation"]
    assert interpolation == {
        "same_phase_progress_interpolation": True,
        "candidate_window_ms": [100, 250],
        "phase_change_applies_on_first_renderable_frame": True,
        "cross_phase_blending": False,
        "next_phase_prediction": False,
        "missing_frame_extrapolation": False,
        "exact_value_freeze_gate": "U-03_EXTERNAL_LATENCY_EVIDENCE",
    }

    recovery_mapping = data["recovery_mapping"]
    assert recovery_mapping == {
        "participant_visible_term": "累计环境状态",
        "technical_contract_term": "RecoveryState",
        "input_range": [0.0, 1.0],
        "bidirectional": True,
        "historical_max_hold": False,
        "forced_full_endpoint": False,
        "candidate_low_pass_seconds": [2, 5],
        "weather_identity_retained_at_high_value": True,
        "initial_curve": "SHARED_LINEAR",
        "weather_specific_curve": False,
        "weather_specific_endpoints": True,
        "nonlinear_change_gate": "U-03_VERSIONED_VISIBILITY_EVIDENCE",
        "same_curve_endpoints_and_timing_between_cue_modes": True,
    }

    confidence = data["actual_confidence_envelope"]
    assert confidence == {
        "shared_across_weather_and_cue_modes": True,
        "controls": ["CONTINUITY", "EDGE_CLARITY", "BOUNDED_OPACITY"],
        "does_not_control": [
            "PHASE",
            "PROGRESS",
            "SPEED",
            "SIZE",
            "PATH_GEOMETRY",
            "COLOR",
        ],
        "jitter_or_flicker": False,
        "low_confidence_remains_locatable": True,
        "exact_value_freeze_gate": "U-03_VISIBILITY_EVIDENCE",
    }

    audio = data["audio_baseline"]
    assert audio == {
        "role": "NON_RHYTHMIC_ENVIRONMENTAL_MASTER_ONLY",
        "reacts_to_target_actual_recovery_or_fallback": False,
        "integrated_loudness_lufs_i": [-24, -20],
        "true_peak_max_dbtp": -3,
        "scene_corridor_crossfade_seconds": [2, 4],
        "prefer_full_module_master": True,
        "minimum_seamless_loop_seconds": 60,
        "loop_point_aligned_with_breath_cycle": False,
        "deterministic_start_at_module_relative_time_zero": True,
        "runtime_random_events": False,
        "pause_freezes_position_and_stops_output": True,
        "resume_from_frozen_position": True,
        "same_file_hash_start_loop_loudness_envelope_between_cue_modes": True,
        "exact_value_freeze_gate": "U-03_AND_U-08_MEASUREMENT_EVIDENCE",
    }

    scroll = data["scroll_parallax_baseline"]
    assert scroll == {
        "camera_motion": "HORIZONTAL_ONLY",
        "fixed_camera_properties": [
            "HEIGHT",
            "ROTATION",
            "ORTHOGRAPHIC_SIZE",
            "HORIZON",
            "CUE_SAFE_AREAS",
        ],
        "base_speed_viewport_widths_per_second": [0.015, 0.025],
        "default_candidate_viewport_widths_per_second": 0.02,
        "candidate_reference_resolution": [1920, 1080],
        "candidate_px_per_second_at_reference_resolution": [28.8, 48.0],
        "default_candidate_px_per_second_at_reference_resolution": 38.4,
        "runtime_records_resolution_and_px_per_second": True,
        "sky_motion": "STATIC",
        "apparent_scroll_factors": {
            "far": [0.3, 0.45],
            "mid": [0.6, 0.8],
            "near_ground": 1.0,
        },
        "maximum_moving_parallax_bands": 3,
        "multiple_asset_layers_may_share_band": True,
        "cue_layers_participate_in_world_parallax": False,
        "same_base_speed_across_weather_and_cue_modes": True,
        "speed_reacts_to_weather_target_actual_or_recovery": False,
        "pause_freezes_all_visual_time_sources": True,
        "pixel_art_candidate_defaults_apply": False,
        "exact_value_freeze_gate": (
            "U-03_PARALLAX_SEAM_AND_PAUSE_EVIDENCE_THEN_U-08"
        ),
    }

    scroll_assets = data["scroll_asset_strategy"]
    assert scroll_assets == {
        "mode": "DETERMINISTIC_SEGMENTED_LONG_SCROLL",
        "fixed_segment_order": True,
        "runtime_random_reordering": False,
        "single_giant_runtime_texture": False,
        "short_visibly_repeating_loop": False,
        "maximum_candidate_module_seconds": 220,
        "maximum_candidate_speed_viewport_widths_per_second": 0.025,
        "minimum_travel_plus_initial_viewport_widths": 6.5,
        "minimum_effective_coverage_viewport_widths": 6.75,
        "recommended_initial_segment_count": 4,
        "maximum_raw_segment_width_viewports": 2.0,
        "overlap_viewport_widths": [0.1, 0.15],
        "overlap_px_at_1920_width": [192, 288],
        "sky_static": True,
        "far_layer_shorter_deterministic_seamless_strip_allowed": True,
        "recognizable_landmark_repetition_within_module": False,
        "shared_canvas_origin_horizon_and_safe_areas": True,
        "repair_hidden_regions_after_layer_split": True,
        "automatic_trim": False,
        "u03_evidence": [
            "STATIC_SEAM_PREVIEW",
            "FULL_DURATION_SCROLL_RECORDING",
        ],
        "rejection_reasons": [
            "VISIBLE_SEAM",
            "TRANSPARENT_HOLE",
            "REPAINT_DISCONTINUITY",
            "OBVIOUS_REPETITION",
        ],
        "exact_segment_and_texture_split_freeze_gate": (
            "F-03_ENGINEERING_BUDGET_AND_U-03_VISUAL_EVIDENCE"
        ),
    }

    composition = data["composition_safe_areas"]
    assert composition == {
        "aspect_ratio": "16:9",
        "coordinate_system": "NORMALIZED_SCREEN_BOTTOM_LEFT_ORIGIN",
        "horizon_y": [0.56, 0.62],
        "default_candidate_horizon_y": 0.59,
        "same_horizon_across_segments_and_cue_modes_within_weather": True,
        "scene_native_target": {"x": [0.55, 0.85], "y": [0.34, 0.72]},
        "scene_native_actual": {"x": [0.2, 0.45], "y": [0.18, 0.52]},
        "target_actual_safe_areas_overlap": False,
        "persistent_foreground_landmark_or_high_contrast_crossing": False,
        "abstract_ring_center": [0.5, 0.5],
        "abstract_outer_ring_max_diameter_short_edge_fraction": [0.18, 0.24],
        "scene_native_target_actual_disabled_in_abstract_mode": True,
        "unity_world_unit_conversion_owner": "F-03",
        "legacy_pixel_camera_parameters_apply": False,
        "exact_value_freeze_gate": (
            "U-03_SAFE_AREA_GRAYSCALE_AND_SCROLL_EVIDENCE"
        ),
    }

    required_consumers = {
        "U-02",
        "V-04",
        "V-05",
        "U-03",
        "U-04",
        "U-05",
        "U-06",
        "U-07",
        "G-02",
        "U-08",
    }
    assert set(data["downstream_consumers"]) == required_consumers

    fill = data["detailed_fill_state"]
    assert fill["mapping_rows"] == 40
    assert fill["parameter_values"] == "CANDIDATE_VALUES_DOCUMENTED_NOT_RUNTIME_FROZEN"
    assert fill["condition_review_results"] == "DESIGN_MATCHED_RUNTIME_EVIDENCE_PENDING"
    assert fill["audio_assets"] == "PLANNED_NOT_PRODUCED_OR_CLEARED"
    assert fill["asset_entries"] == "PLANNED_PENDING_G02_CLEARANCE"
    assert fill["weather_risk_scores"] == "DUAL_SCORING_COMPLETE_DIFFERENCES_RESOLVED"
    assert fill["u03_selected_weather"] == "fade"
    assert fill["independent_agent_review"] == "PASS_NO_OPEN_P0_P2"
    assert fill["storm_phase_instances"] == "LOGICAL_SLOT_READY_RUNTIME_BINDING_F05"
    assert fill["fade_phase_instances"] == "LOGICAL_SLOT_READY_RUNTIME_BINDING_F05"

    plan = plan_path.read_text(encoding="utf-8")
    for required_text in (
        "Python",
        "Unity",
        "TouchDesigner",
        "TargetCue",
        "ActualFeedback",
        "RecoveryState",
        "FallbackState",
        "CANDIDATE_READY_FOR_SECOND_PERSON_REVIEW",
    ):
        assert required_text in plan, f"missing planning boundary: {required_text}"

    print(
        "PASS: V-03 preparation baseline; "
        "deliverable_templates=6; risk_dimensions=7; "
        "candidate=ready_for_second_person_review; "
        "F05_runtime_binding=deferred"
    )


if __name__ == "__main__":
    main()
