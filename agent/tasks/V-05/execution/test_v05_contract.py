import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / 'agent/tasks/V-05'
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def test_current_state_and_actual_delivery_are_not_invented():
    with (PLAN / '24_团队任务与项目治理/05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'V-05')
    current = read(TASK / 'outputs/current-graybox.json')
    assert row['status'] == current['status'] == 'READY'
    assert set(row['depends_on'].split('|')) == set(current['depends_on'])
    assert current['process_profile'] == row['process_profile'] == 'P-DEV'
    assert current['claimant'] is None
    assert not current['unity_graybox_implemented']
    assert not current['full_graybox_video_verified']
    assert not current['human_formative_review_done'] and not current['formal_use_allowed']


def test_current_journey_camera_and_timing_align():
    current = read(TASK / 'outputs/current-graybox.json')
    journey = read(ROOT / current['journey_source'])
    preview = read(ROOT / current['preview_source'])
    for field in ('runtime_schema_version', 'conditions', 'module_ids', 'camera',
                  'sequence_authority', 'clock_authority', 'unity_independent_of_td', 'native_is_hidden'):
        assert current[field] == journey[field]
    assert current['core_segments'] == journey['segments']
    assert current['core_default_seconds'] == journey['default_core_seconds'] == 800
    assert current['condition_training_budget_seconds'] == journey['training_budget_seconds'] is None
    assert not current['condition_training_inside_core'] and not current['unity_reads_questionnaire_answers']
    assert not preview['core_preview_includes_condition_training']
    assert current['fade_fullscreen_color_source'] == journey['fade_fullscreen_color_source'] == preview['fade_fullscreen_color_source']
    phases = [x['phase'] for x in journey['journey']]
    assert phases.index('panas_pre') < phases.index('condition_training') < phases.index('demo')
    assert phases.index('panas_post') < phases.index('understanding_and_other_measures')
    assert len(journey['journey']) == 14


def test_core_matrix_is_explicitly_host_only():
    report = read(TASK / 'evidence/runtime/core-matrix.json')
    assert report['case_count'] == len(report['cases']) == 48
    assert report['sequence_count'] == 24
    assert report['scope'] == 'HOST_CORE_ONLY_NOT_UNITY'
    assert report['acks'] == 'SYNTHETIC_HOST_FIXTURE'
    assert report['unity_render_receipts'] == report['external_journey_runtime'] == report['human_formative_review'] == 'NOT_RUN'
    assert all(case['schema_version'] == '2.2' and case['runtime_mode'] == 'dev_replay' and case['source_policy'] == 'replay' for case in report['cases'])
    assert all(case['status'] == 'COMPLETED' and case['core_elapsed_ns'] == 800_000_000_000 for case in report['cases'])
