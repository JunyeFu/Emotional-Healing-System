"""Record existing fixture behavior; this is not a runtime approval gate."""
import json
from pathlib import Path
import runpy
import sys

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
TECH = ROOT / '02-技术研发'
sys.path.insert(0, str(TECH))

from srp_session_core import SessionCore, SessionCoreError


def observe():
    fixtures = runpy.run_path(str(TECH / 'tests/session_core/conftest.py'))
    manifest = fixtures['manifest_factory'].__wrapped__()(runtime_mode='formal_stage_1')
    assignment = fixtures['assignment_factory'].__wrapped__()(manifest)
    try:
        SessionCore().prepare(manifest, assignment, 0)
    except SessionCoreError as error:
        default = {'result': 'REJECTED', 'code': error.code, 'detail': error.detail}
    else:
        default = {'result': 'ACCEPTED'}
    dependencies = runpy.run_path(str(TECH / 'tests/session_core/helpers.py'))['formal_dependencies']()
    update = SessionCore(dependencies=dependencies).prepare(manifest, assignment, 0)
    return {'task_id': 'U12-06', 'scope': 'EXISTING_SYNTHETIC_FIXTURE_ONLY',
            'default_formal': default,
            'synthetic_formal': {'status': update.snapshot.status.value, 'control_events': len(update.control_events),
                                'gate_evidence_ids': [item.evidence_id for item in update.gate_receipts]},
            'real_approval_read': False, 'formal_research_gate_delivered': False,
            'tcp_udp_sent': False, 'real_exposure_registered': False}


if __name__ == '__main__':
    report = observe()
    (TASK / 'evidence/runtime-observations.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
