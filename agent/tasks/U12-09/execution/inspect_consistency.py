"""Build read-only current indices without certifying runtime or study readiness."""
import csv
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
resolve_path = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_project_path']
PLAN = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
ADAPT = PLAN.parent / '2026-09-08_SRP_v1.2_当前基线适配包'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(value):
    return hashlib.sha256(value).hexdigest().upper()


def legacy_observations():
    binding = read(GOV / 'u12_upgrade/legacy_evidence_binding.json')
    results = []
    for upgrade, entries in binding['entries'].items():
        for item in entries:
            if item['original_byte_identity'] != 'UNRESOLVED_WORKTREE_BYTES':
                continue
            blob = subprocess.check_output(['git', 'show', binding['commit'] + ':' + item['repository_path']], cwd=ROOT)
            lf = blob.replace(b'\r\n', b'\n')
            candidates = {'historical_git_blob': blob, 'historical_lf': lf, 'historical_crlf': lf.replace(b'\n', b'\r\n'),
                          'historical_bom_lf': b'\xef\xbb\xbf' + lf.removeprefix(b'\xef\xbb\xbf'),
                          'historical_bom_crlf': b'\xef\xbb\xbf' + lf.removeprefix(b'\xef\xbb\xbf').replace(b'\n', b'\r\n')}
            baseline = ADAPT / 'baseline' / Path(item['repository_path']).name
            if baseline.is_file():
                candidates['adapter_baseline_bytes'] = baseline.read_bytes()
            live = resolve_path(ROOT, item['repository_path'])
            candidates['current_worktree_not_historical'] = live.read_bytes()
            observed = {name: digest(value) for name, value in candidates.items()}
            results.append({'upgrade': upgrade, 'reference': item['reference'],
                            'repository_path': item['repository_path'],
                            'declared_original_byte_sha256': item['original_declared_byte_sha256'],
                            'historical_git_identity_matches': digest(blob) == item['git_blob_sha256'],
                            'candidate_hashes': observed,
                            'matching_candidate_sources': [name for name, value in observed.items() if value == item['original_declared_byte_sha256']],
                            'original_binding_status': item['original_byte_identity']})
    return {'scope': 'BOUNDED_ACCESSIBLE_SOURCE_CHECK_NOT_EXHAUSTIVE_RECOVERY',
            'original_binding_unchanged': True, 'references': results}


def consumer_rows():
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    result = []
    for entry in read(GOV / 'u12_upgrade/consumers.json')['entries']:
        base = PLAN if entry['root'] == 'plan' else ROOT
        result.append({'consumer_id': entry['id'], 'owner_task': entry['owner'],
                       'owner_claimant': registry[entry['owner']]['claimant'] or '未领取',
                       'registered_status': registry[entry['owner']]['status'],
                       'declared_consumer_status': entry['status'],
                       'repository_path': (base / entry['path']).relative_to(ROOT).as_posix(),
                       'path_exists': (base / entry['path']).is_file(),
                       'acceptance_path': entry.get('acceptance_path', ''),
                       'evidence_limit': entry.get('limit', '静态索引；不证明真实运行或新研究签收')})
    return result


def done_rows():
    result = []
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['status'] != 'DONE':
                continue
            relative = f"agent/tasks/{row['task_id']}/outputs/summary.json"
            summary = read(ROOT / relative)
            accepted = summary['historical_acceptance']
            result.append({'task_id': row['task_id'], 'registered_status': row['status'],
                           'registered_reviewer': row['reviewer'],
                           'reported_historical_reviewer': accepted['reviewer'],
                           'reported_historical_candidate': accepted.get('commit') or '',
                           'current_scope_and_pending': summary['conclusion'],
                           'source': relative,
                           'new_scope_acceptance_inferred': False})
    return result


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def csv_bytes(rows):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def artifacts():
    consumers = consumer_rows()
    legacy = legacy_observations()
    protocol = read(PLAN / '00_总控/protocol_authority_v1.2.json')
    fields = {'training.budget_seconds': protocol['training']['budget_seconds'],
              'primary.minimum_important_affect_difference': protocol['primary']['minimum_important_affect_difference'],
              'functional_guard.critical_module_error_thresholds': protocol['functional_guard']['critical_module_error_thresholds'],
              'sample_planning.formal_randomized_n': protocol['sample_planning']['formal_randomized_n'],
              'missingness.model_and_mnar_grid': protocol['missingness']['model_and_mnar_grid']}
    counts = {}
    for entry in consumers:
        status = entry['declared_consumer_status']
        counts[status] = counts.get(status, 0) + 1
    report = {'task_id': 'U12-09', 'scope': 'STATIC_AND_EXISTING_SOFTWARE_ONLY_NOT_BUSINESS_ACCEPTANCE',
              'consumer_count': len(consumers), 'consumer_status_counts': counts,
              'all_consumer_paths_exist': all(row['path_exists'] for row in consumers),
              'registered_done_count': len(done_rows()),
              'formal_blank_fields': [name for name, value in fields.items() if value is None],
              'formal_authorization': False, 'formal_gate_proved': False,
              'legacy_unresolved_references': len(legacy['references']),
              'legacy_declared_byte_matches_in_checked_sources': sum(bool(row['matching_candidate_sources']) for row in legacy['references']),
              'new_independent_review': 'NOT_RUN', 'new_human_acceptance': 'NOT_SIGNED',
              'root_migration_complete': False}
    return {'consumer-matrix.csv': csv_bytes(consumers), 'old-done-impact.csv': csv_bytes(done_rows()),
            'legacy-byte-observations.json': json_bytes(legacy), 'current-consistency.json': json_bytes(report)}


if __name__ == '__main__':
    for name, value in artifacts().items():
        (TASK / 'outputs' / name).write_bytes(value)
    print('WROTE current indices; no formal authority or business PASS issued')
