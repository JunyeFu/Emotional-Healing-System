import csv
import hashlib
from itertools import permutations
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
MODULE = ROOT / '02-技术研发/08-随机化'
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(TASK / 'execution'))
from srp_randomization import generate_list, policy_decisions, SnapshotGateEvidenceVerifier, RandomizationStore
from srp_randomization.models import AllocationReceipt
from verify_x01 import verify


def current():
    return json.loads((TASK / 'outputs/current-randomization.json').read_text(encoding='utf-8'))


def test_registry_and_real_historical_signoff_scope():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        row = next(r for r in csv.DictReader(stream) if r['task_id'] == 'X-01')
    value = current()
    assert value['business_status'] == row['status'] == 'DONE'
    assert value['depends_on'] == row['depends_on'].split('|')
    assert value['claimant'] == row['claimant'] == 'Codex'
    report = (ROOT / '03-测试与实验/X-01_第二人审核报告_已签署.md').read_text(encoding='utf-8')
    for field in ('reviewer', 'date', 'candidate', 'signature_commit'):
        assert value['historical_acceptance'][field] in report
    assert value['current_tool_revision_signed'] is False
    assert value['historical_acceptance']['scope'] == 'ORIGINAL_SOFTWARE_AND_SYNTHETIC_ONLY'


def test_actual_config_fixed_blocks_and_open_formal_context():
    config = json.loads((MODULE / 'config/randomization_config_v1.0.json').read_text(encoding='utf-8'))
    value = current()
    assert value['block_size'] == config['allocation_block_size'] == 48
    assert value['supported_stages'] == list(config['stages'])
    assert value['variable_block_size_supported'] is value['supports_level_c'] is False
    assert value['required_reveal_gates'] == config['required_reveal_gates']
    assert value['formal_role_assignments'] is value['formal_strata_cutpoints'] is value['formal_randomization_list'] is None
    assert value['roles_are_operating_system_authentication'] is False
    assert value['real_activity'] == 'NOT_RUN'


def test_snapshot_replay_does_not_get_formal_gate_by_declaration(tmp_path):
    verifier = SnapshotGateEvidenceVerifier()
    store = RandomizationStore(tmp_path / 'synthetic.sqlite', evidence_verifier=verifier, formal_capable=True)
    assert verifier.formal_capable is store.formal_capable is current()['snapshot_verifier_formal_capable'] is False


def test_all_sequence_decisions_have_interval_witness_not_state_or_rng():
    assert current()['random_draw_is_runtime_rng_log'] is False
    for sequence in permutations(('storm', 'heat', 'snow', 'fade')):
        decisions = policy_decisions(session_id='SYNTHETIC-X01-CURRENT', stage='stage_1', sequence=sequence, created_monotonic_ns=0)
        assert [d['behavior_probability'] for d in decisions] == current()['sequence_probabilities']
        for decision in decisions:
            candidates = decision['candidate_actions']
            selected = candidates.index(decision['selected_action'])
            assert decision['random_draw'] == (selected + 0.5) / len(candidates)
            assert decision['reason_code'] == 'BALANCED_LIST_UNIFORM_WITHOUT_REPLACEMENT'


def test_frozen_policy_list_is_not_runtime_assignment():
    plan = generate_list('stage_3', ('synthetic',), 1, b'x01-handoff-fixture')
    record = next(r for r in plan.records if r.arm == 'frozen_policy')
    assert record.weather_sequence is current()['frozen_policy_sequence_in_list'] is None
    receipt = AllocationReceipt(record.allocation_index, record.stage, record.stratum, record.block,
                                record.arm, None, record.arm_behavior_probability, plan.list_hash, '1.0',
                                'synthetic-permit', 'synthetic-reservation', 'synthetic-evidence')
    assert receipt.policy_decisions('SYNTHETIC', 0) == ()
    with pytest.raises(RuntimeError, match='FROZEN_POLICY_SEQUENCE_REQUIRES_X03'):
        receipt.to_assignment_bundle('SYNTHETIC', 0)
    assert current()['stage_3_policy_runtime_complete'] is False


def test_actual_tools_moved_and_old_readme_bytes_preserved():
    assert not (MODULE / 'verify_x01.py').exists()
    assert not (MODULE / 'generate_evidence.py').exists()
    assert hashlib.sha256((TASK / 'archive/README_legacy.md').read_bytes()).hexdigest().upper() == '9BE5CC4CE6C86C606444B1CE3B71DAE9BA8F2ED3AA559FD521E056A84CB016E2'
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
    for path in sources['paths']:
        assert (ROOT / path).exists(), path


def test_real_cli_reproduces_six_original_artifacts_without_overwriting(tmp_path):
    output = tmp_path / 'new-synthetic-evidence'
    command = [sys.executable, str(TASK / 'execution/generate_evidence.py'), '--output-root', str(output)]
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env)
    assert run.returncode == 0, run.stderr
    files = sorted(p for p in output.rglob('*.json'))
    assert len(files) == 6
    before = {p.relative_to(output): p.read_bytes() for p in files}
    for path in files:
        assert json.loads(path.read_text(encoding='utf-8')) == json.loads((MODULE / path.relative_to(output)).read_text(encoding='utf-8'))
    assert verify(output) == []
    repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', env=env)
    assert repeated.returncode != 0 and 'FileExistsError' in repeated.stderr
    assert before == {p.relative_to(output): p.read_bytes() for p in files}


def test_original_reports_signatures_schema_and_business_code_unchanged():
    protected = [str((MODULE / part).relative_to(ROOT)) for part in ('fixtures', 'evidence', 'contracts', 'config', 'srp_randomization', 'X-01_技术验收记录.md')]
    protected += ['03-测试与实验/X-01_第二人审核报告_已签署.md', '03-测试与实验/X-01_独立Agent复审报告_2026-09-06.md']
    run = subprocess.run(['git', 'diff', '--exit-code', '43d1a4b', '--', *protected], cwd=ROOT, capture_output=True)
    assert run.returncode == 0, run.stdout.decode('utf-8', errors='replace')
