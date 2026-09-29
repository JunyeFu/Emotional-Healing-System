import hashlib
import json
from pathlib import Path
import runpy

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def test_actual_archives_and_preserved_acceptance():
    current = read(TASK / 'outputs/current-measurement.json')
    for name, expected in current['archive_byte_sha256'].items():
        assert hashlib.sha256((TASK / 'archive' / name).read_bytes()).hexdigest().upper() == expected
    assert hashlib.sha256((TASK / 'outputs/annotation-plan.md').read_bytes()).hexdigest().upper() == current['annotation_plan_byte_sha256']
    assert hashlib.sha256((GOV / 'u12_upgrade/acceptance/U12-02.json').read_bytes()).hexdigest().upper() == current['acceptance_byte_sha256']
    assert not (ROOT / 'agent/modules/srp_step_measurement/task_state.py').exists()
    assert not (ROOT / 'agent/modules/srp_step_measurement/build_evidence.py').exists()

def test_original_synthetic_bytes_and_current_materials_match():
    original = TASK / 'archive/signed-candidate'
    for name, digest in read(original / 'sha256.json').items():
        assert hashlib.sha256((original / name).read_bytes()).hexdigest() == digest
    artifacts = runpy.run_path(str(TASK / 'execution/build_evidence.py'))['artifacts']()
    for name in ('input_cases.json', 'participant_items.json', 'private_answer_keys.json'):
        assert artifacts[name] == (original / name).read_bytes()
        assert artifacts[name] == (TASK / 'outputs/materials' / name).read_bytes()
    assert read(original / 'verification.json')['source_text_sha256_lf']['02-技术研发/srp_step_measurement/build_evidence.py'] == hashlib.sha256((TASK / 'archive/build_evidence.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()

def test_current_and_original_scope_not_relabelled():
    current = read(TASK / 'outputs/current-measurement.json')
    assert current['business_status'] == 'DONE' and not current['formal_ready']
    assert current['new_human_acceptance'] == 'NOT_SIGNED'
    for directory in (TASK / 'archive/signed-candidate', TASK / 'outputs/materials'):
        report = read(directory / 'verification.json')
        assert report['case_count'] == 15 and report['evidence_class'] == 'SYNTHETIC_ONLY'
        assert not report['real_annotation_validated'] and not report['formal_ready']
        assert all(c['clip_render_review'] == 'PENDING' for c in report['cases'])
    original = read(GOV / 'u12_upgrade/acceptance/U12-02.json')
    assert original['candidate_commit'] == current['candidate_commit']
    assert original['independent_review']['reviewer'] == 'Carson'

def test_runtime_measurement_and_sources_exist():
    old = read(TASK / 'archive/signed-candidate/verification.json')
    expected = old['source_text_sha256_lf']['02-技术研发/srp_step_measurement/measurement.py']
    actual = ROOT / 'agent/modules/srp_step_measurement/measurement.py'
    assert hashlib.sha256(actual.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == expected
    for path in read(TASK / 'inputs/sources.json')['paths']:
        assert (ROOT / path).is_file()
    plan = (TASK / 'outputs/annotation-plan.md').read_text(encoding='utf-8')
    assert 'SPECIFICATION_ONLY' in plan and 'PANAS后测之后' in plan
