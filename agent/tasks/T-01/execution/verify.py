"""Verify current T-01 code and distinguish signed evidence from the cleaned TOE."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
MODULE = ROOT / 'agent/modules/03-TouchDesigner/t01_telemetry_panel'
sys.path.insert(0, str(MODULE))
from t01_node_plan import write_host_artifacts

CANDIDATE = '8790cd3ae4db3543c038efc21deec635605cb06f'
PREFIX = MODULE.relative_to(ROOT).as_posix()


def git_artifact_policy(original, signed_bytes):
    if original == signed_bytes:
        return 'raw_bytes'
    if original.startswith(b'version https://git-lfs.github.com/spec/v1'):
        fields = dict(line.split(b' ', 1) for line in original.splitlines())
        if fields.get(b'oid') != b'sha256:' + sha256(signed_bytes).hexdigest().encode('ascii') or fields.get(b'size') != str(len(signed_bytes)).encode('ascii'):
            raise ValueError('LFS_POINTER_IDENTITY_MISMATCH')
        return 'lfs_pointer_vs_materialized_artifact'
    if original.replace(b'\r\n', b'\n') == signed_bytes.replace(b'\r\n', b'\n'):
        return 'git_normalized_text_vs_signed_checkout_bytes'
    raise ValueError('UNEXPLAINED_SIGNED_SOURCE_DRIFT')


def compare_core_files(original_dir, original_entries, current_dir, current_entries):
    def core_entry(path):
        return path.startswith('project1/T01_TelemetryPanel.') or path.startswith('project1/T01_TelemetryPanel/')
    core = {p for p in original_entries if core_entry(p)}
    current_core = {p for p in current_entries if core_entry(p)}
    differences = sorted(core ^ current_core)
    layout_only = []
    for p in sorted(core & current_core):
        before, after = (original_dir / p).read_bytes(), (current_dir / p).read_bytes()
        if before == after:
            continue
        if p.endswith('.n'):
            def without_editor_layout(content):
                return [line.replace(' current on', '') for line in content.decode('utf-8').splitlines()
                        if not line.startswith(('tile ', 'v '))]
            if without_editor_layout(before) == without_editor_layout(after):
                layout_only.append(p)
                continue
        differences.append(p)
    return len(core), differences, layout_only


def main():
    evidence = TASK / 'evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    tests = [str(MODULE / 'tests'),
             str(ROOT / 'agent/modules/03-TouchDesigner/f04_readonly_console/tests'),
             str(TASK / 'execution/test_verify.py')]
    result = subprocess.run([sys.executable, '-m', 'pytest', *tests, '-q'],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    (evidence / 'pytest.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    write_host_artifacts(evidence / 'host')
    manifest = json.loads((MODULE / 'evidence/evidence_manifest.json').read_text(encoding='utf-8'))
    comparisons = []
    for relative, expected in manifest['artifacts'].items():
        original = subprocess.check_output(['git', 'show', f'{CANDIDATE}:{PREFIX}/{relative}'], cwd=ROOT)
        current = (MODULE / relative).read_bytes()
        historical_hash = sha256(original).hexdigest().upper()
        if relative == 'T01_TelemetryPanel.toe':
            signed_bytes = original
        elif sha256(current).hexdigest().upper() == expected['sha256']:
            signed_bytes = current
        else:
            raise ValueError(f'SIGNED_EVIDENCE_MISMATCH:{relative}')
        if sha256(signed_bytes).hexdigest().upper() != expected['sha256'] or len(signed_bytes) != expected['bytes']:
            raise ValueError(f'SIGNED_EVIDENCE_MISMATCH:{relative}')
        git_policy = git_artifact_policy(original, signed_bytes)
        comparisons.append({'path': relative, 'signed_sha256': expected['sha256'],
                            'git_blob_sha256': historical_hash, 'git_policy': git_policy,
                            'current_sha256': sha256(current).hexdigest().upper(),
                            'same_bytes': current == signed_bytes})
    changed = [item['path'] for item in comparisons if not item['same_bytes']]
    if changed != ['T01_TelemetryPanel.toe']:
        raise ValueError(f'UNEXPLAINED_SIGNED_EVIDENCE_DRIFT:{changed}')
    cleanup = json.loads((MODULE / 'design/default-demo-cleanup-report.json').read_text(encoding='utf-8-sig'))
    toe_hash = sha256((MODULE / 'T01_TelemetryPanel.toe').read_bytes()).hexdigest().upper()
    scratch = ROOT / '.artifacts-local/task-normalization/T-01/identity' / time.strftime('%Y%m%d-%H%M%S')
    scratch.mkdir(parents=True)
    expanded = []
    for label, content in [('signed', subprocess.check_output(['git', 'show', f'{CANDIDATE}:{PREFIX}/T01_TelemetryPanel.toe'], cwd=ROOT)),
                           ('current', (MODULE / 'T01_TelemetryPanel.toe').read_bytes())]:
        toe = scratch / (label + '.toe')
        toe.write_bytes(content)
        run = subprocess.run(['D:/TouchDesigner/bin/toeexpand.exe', str(toe)], capture_output=True, text=True)
        toc = Path(str(toe) + '.toc')
        if not toc.exists():
            raise RuntimeError(run.stdout + run.stderr)
        expanded.append((Path(str(toe) + '.dir'), toc.read_text(encoding='utf-8').splitlines()))
    original_dir, original_entries = expanded[0]
    current_dir, current_entries = expanded[1]
    core_count, core_differences, layout_only = compare_core_files(original_dir, original_entries, current_dir, current_entries)
    demo = ('geo1', 'noise1', 'chopto1', 'displace1', 'moviefilein1', 'out1')
    remaining_demo = [p for p in current_entries if any(p.startswith(f'project1/{name}.') or p.startswith(f'project1/{name}/') for name in demo)]
    display_bound = 'top 0 ./T01_TelemetryPanel/Output/display_out' in (current_dir / 'project1.parm').read_text(encoding='utf-8')
    cleanup_comparison = {'signed_core_files': core_count, 'functional_differences': core_differences,
                          'editor_layout_only': layout_only,
                          'remaining_demo_entries': remaining_demo, 'display_bound': display_bound,
                          'old_cleanup_candidate_sha256': cleanup['candidate_sha256'], 'current_toe_sha256': toe_hash}
    (evidence / 'cleanup_comparison.json').write_text(json.dumps(cleanup_comparison, indent=2) + '\n', encoding='utf-8')
    if core_differences or remaining_demo or not display_bound:
        raise ValueError(f'CURRENT_CLEANUP_CONTENT_MISMATCH:{cleanup_comparison}')
    (evidence / 'artifact_comparison.json').write_text(
        json.dumps({'candidate': CANDIDATE, 'artifacts': comparisons}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    checks = [
        {'command': 'pytest T-01 + F-04', 'exit_code': 0, 'result': result.stdout.strip()},
        {'command': 'write_host_artifacts', 'exit_code': 0, 'result': 'Current node, field and permission plans generated'},
        {'command': 'signed Git bytes and current artifact identity', 'exit_code': 0,
         'result': '23 signed artifacts verified with explicit Git text/LFS policy; current TOE retains all signed core files and removes root demos',
         'source': 'agent/tasks/T-01/evidence/artifact_comparison.json'},
    ]
    runtime = evidence / 'runtime/probe_report.json'
    if runtime.exists():
        report = json.loads(runtime.read_text(encoding='utf-8'))
        runtime_source = ROOT / report['source_toe']
        if not report['pass'] or report['source_toe_sha256'] != sha256(runtime_source.read_bytes()).hexdigest().upper():
            raise ValueError('CURRENT_RUNTIME_PROBE_MISMATCH')
        checks.append({'command': 'run_td_probe.py', 'exit_code': 0,
                       'result': report['checks'], 'source': 'agent/tasks/T-01/evidence/runtime/probe_report.json'})
    (evidence / 'verification.json').write_text(json.dumps(
        {'task_id': 'T-01', 'review_date': '2026-09-28', 'checks': checks,
         'scope': 'Read-only TD candidate verification, not real-device or final A-theme acceptance'},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result.stdout.strip())
    print('T01_CURRENT_CODE_AND_ARTIFACTS_PASS')


if __name__ == '__main__':
    main()
