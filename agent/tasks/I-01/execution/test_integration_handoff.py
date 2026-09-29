import csv
import json
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def current():
    return json.loads((TASK / 'outputs/current-integration.json').read_text(encoding='utf-8'))


def errors(value):
    expected = current()
    fields = ('session_authority', 'recording_authority', 'same_recording_core_for_host_and_server',
              'td_required_for_experience', 'spout_required_for_experience', 'formal_fixture_allowed',
              'render_receipt_is_external_display_measurement', 'foreign_clock_direct_subtraction_allowed')
    invariants = ('P-01', 'P-02', True, False, False, False, False, False)
    findings = [key for key, required in zip(fields, invariants) if value[key] != required]
    if value['formal_acceptance'] != 'NOT_EVALUATED' or value['observed_evidence']:
        findings.append('unobserved real evidence')
    if value['default_core_seconds'] != 800 or value['host_matrix'] != {'weather_permutations': 24, 'prompt_conditions': 2}:
        findings.append('core coverage')
    for field in ('latency_p95_limit_ms', 'clock_offset_limit_ns', 'clock_drift_limit_ppm', 'sync_uncertainty_limit_ns', 'stress_duration_hours'):
        if value[field] is not None:
            findings.append('unfrozen ' + field)
    if value['depends_on'] != expected['depends_on']:
        findings.append('dependency drift')
    return findings


def test_matches_actual_registry_and_pending_owner():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(row for row in csv.DictReader(stream) if row['task_id'] == 'I-01')
    value = current()
    assert errors(value) == []
    assert value['business_status'] == row['status'] == 'WAIT_DEP_EXTERNAL'
    assert value['depends_on'] == row['depends_on'].split('|')
    assert row['claimant'] == row['reviewer'] == ''
    assert value['claimant'] is value['reviewer'] is None


@pytest.mark.parametrize('field,bad', [
    ('session_authority', 'Unity'), ('recording_authority', 'TD'),
    ('same_recording_core_for_host_and_server', False), ('td_required_for_experience', True),
    ('spout_required_for_experience', True), ('formal_fixture_allowed', True),
    ('render_receipt_is_external_display_measurement', True), ('foreign_clock_direct_subtraction_allowed', True),
    ('formal_acceptance', 'PASS'), ('observed_evidence', ['LIVE_E2E']),
    ('default_core_seconds', 600), ('latency_p95_limit_ms', 500), ('stress_duration_hours', 2),
])
def test_rejects_false_assembly_or_unperformed_acceptance(field, bad):
    value = current()
    value[field] = bad
    assert errors(value)


def test_sources_and_software_receipt_identity():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for source in sources['paths']:
        assert (ROOT / source).exists(), source
    receipt_path = next(path for path in sources['paths'] if path.endswith('render-receipt.json'))
    receipt = json.loads((ROOT / receipt_path).read_text(encoding='utf-8'))
    assert receipt['schema_version'] == '2.2'
    assert receipt['message_type'] == 'render_receipt'
    assert 'rendered_monotonic_ns' in receipt
    assert 'external_display_time' not in receipt
