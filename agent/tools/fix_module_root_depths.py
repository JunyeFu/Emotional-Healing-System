"""Repair explicitly identified repository-depth consumers after the modules move."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPLACEMENTS = {
    'tests/test_u12_governance.py': [('parents[2]', 'parents[3]')],
    'tests/test_task_package_hash_policy.py': [('parents[2]', 'parents[3]')],
    'tests/test_audit_upgrade_governance.py': [('parents[2]', 'parents[3]')],
    'tests/a03_spec/test_schema.py': [('parents[3]', 'parents[4]')],
    'tests/a03_spec/test_estimands.py': [('parents[3]', 'parents[4]')],
    'tests/step_measurement/test_measurement.py': [('parents[3]', 'parents[4]')],
    'tests/randomization/test_verifier.py': [('ROOT.parents[1]', 'ROOT.parents[2]')],
    'tests/session_store/test_golden_archive.py': [('parents[3]', 'parents[4]')],
    'tests/session_store/test_recording_replay.py': [('parents[3]', 'parents[4]')],
    '05-通信协议/tests/contract/test_f05_evidence.py': [('parents[4]', 'parents[5]')],
    '07-数据治理/tests/test_unity_gate.py': [('parents[3]', 'parents[4]')],
    '07-数据治理/tests/test_privacy.py': [('parents[3]', 'parents[4]')],
    '07-数据治理/tests/conftest.py': [('MODULE_ROOT.parents[1]', 'MODULE_ROOT.parents[2]')],
    '03-TouchDesigner/f04_readonly_console/tests/test_f04_console.py': [('ROOT.parents[2]', 'ROOT.parents[3]')],
    '03-TouchDesigner/t01_telemetry_panel/tests/test_workbench_view.py': [('BASE.parents[2]', 'BASE.parents[3]')],
    '03-TouchDesigner/t01_telemetry_panel/tests/test_t01_telemetry.py': [('BASE.parents[2]', 'BASE.parents[3]')],
}


def main():
    changed = []
    for relative, replacements in REPLACEMENTS.items():
        path = ROOT / 'agent/modules' / relative
        before = path.read_bytes()
        text = before.decode('utf-8-sig')
        for old, new in replacements:
            if old not in text:
                raise ValueError('Expected original expression missing: ' + relative)
            text = text.replace(old, new)
        path.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8'))
        changed.append(path.relative_to(ROOT).as_posix())
    attributes = ROOT / '.gitattributes'
    attributes.write_bytes(attributes.read_bytes().replace('02-技术研发/'.encode(), b'agent/modules/'))
    changed.extend(['agent/modules/srp_session_core/gates.py',
                    'agent/modules/05-通信协议/csv_logger.py',
                    'agent/modules/05-通信协议/contracts/verify_f05_v22.py',
                    'agent/modules/04-Unity视觉/SRP-Weather-Visual/Assets/U01/Editor/U01EvidenceBuilder.cs',
                    'agent/modules/04-Unity视觉/SRP-Weather-Visual/Assets/Scripts/Editor/FormalBuildGate.cs'])
    evidence = ROOT / 'agent/evidence'
    (evidence / 'root-migration-modules-manual.json').write_text(json.dumps({'files': changed}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    mapping_path = ROOT / 'agent/normalization-relocations.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    for binding in json.loads((evidence / 'root-migration-modules-inputs.json').read_text(encoding='utf-8'))['bindings']:
        current = ROOT / 'agent/modules' / binding['old_project_path'].split('/', 1)[1]
        if current.read_bytes() != (ROOT / binding['new_project_path']).read_bytes() and binding not in mapping['frozen_sources']:
            mapping['frozen_sources'].append(binding)
    mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Repaired', len(REPLACEMENTS), 'repository-depth consumers')


if __name__ == '__main__':
    main()
