"""Check current G-01 usage against its signed scope and live authorities."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0'
GOV = PLAN / '24_团队任务与项目治理'
TASK = ROOT / 'agent/tasks/G-01'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    checks = []

    def record(name, condition, result):
        if not condition:
            raise ValueError(name)
        checks.append({'command': name, 'exit_code': 0, 'result': result})

    sources = read_json(TASK / 'inputs/sources.json')['paths']
    record('source locations', all((ROOT / p).exists() for p in sources), f'{len(sources)} source locations exist')
    material_dir = PLAN / '06_步骤05_伦理与预试材料'
    materials = list(material_dir.glob('G-01-*.md'))
    archived_11 = ROOT / 'agent/tasks/E-01/archive/G-01-11_伦理提交执行检查清单.md'
    materials.append(archived_11)
    ids = sorted(int(re.match(r'G-01-(\d+)_', p.name)[1]) for p in materials)
    record('signed material completeness', ids == list(range(1, 13)), '12 historical materials present; not approved new-study materials')
    unchanged = subprocess.check_output(
        ['git', 'diff', 'HEAD', '--', *(str(p.relative_to(ROOT)) for p in materials if p != archived_11),
         '03-测试与实验/G-01_G-02_治理修复团队总监签收报告_已签署.md'], cwd=ROOT)
    record('historical originals', not unchanged, 'Historical material and signed report bytes unchanged from HEAD')
    original_hash = read_json(ROOT / 'agent/tasks/E-01/inputs/sources.json')['archived_bytes'][archived_11.name]
    record('archived historical material 11', hashlib.sha256(archived_11.read_bytes()).hexdigest().upper() == original_hash,
           'Material 11 is physically archived with original bytes; current step-seven file is navigation only')

    registry = {r['task_id']: r for r in read_csv(GOV / '05_可领取任务包.csv')}
    record('registered scope', registry['G-01']['status'] == 'DONE'
           and registry['G-05']['status'] == 'WAIT_DEP_EXTERNAL'
           and registry['P-02']['status'] == 'DONE', 'G-01/P-02 DONE; G-05 external work pending')
    authority = read_json(PLAN / '00_总控/protocol_authority_v1.2.json')
    training = read_json(ROOT / 'agent/tasks/U12-03/outputs/contract.json')
    sequence = training['timeline']
    record('baseline and training order', sequence.index('panas_pre') < sequence.index('allocation_reveal')
           < sequence.index('condition_training') < sequence.index('core_800s')
           < sequence.index('panas_post'), 'Baseline precedes condition reveal/training; post precedes understanding')
    record('research remains unfrozen', not authority['formal_participant_collection_allowed']
           and not training['formal_collection_allowed']
           and training['formal_training_budget_seconds'] is None
           and training['timeline_status'] == 'PROPOSED_REQUIRES_U12_04_U12_11_FREEZE',
           'Candidate timeline and 180-second teaching do not authorize formal collection')
    record('historical capacity arithmetic', math.floor(360 / 70) == 5
           and math.floor(420 / 55) == 7 and 4 * 5 * 7 == 140
           and 140 * .8 == 112 and math.ceil(112 / .85 / .80) == 165,
           '5/7 theoretical daily slots, 140/112 historical rehearsal, 165 appointments; not observed capacity')
    capabilities = read_csv(GOV / 'audit_upgrade/external_capability_matrix_v1.0.csv')
    record('external qualification state', len(capabilities) == 13
           and all(r['status'] == 'PENDING_EXTERNAL' and not r['evidence_ref'] for r in capabilities),
           '13 external qualifications pending; none converted to authorization')

    current = (TASK / 'outputs/current-governance.md').read_text(encoding='utf-8')
    expected = ['PANAS前测', 'PROPOSED_REQUIRES_U12_04_U12_11_FREEZE',
                'formal_collection_allowed=false', '历史完整路线预算', 'HMAC',
                '角色定义不是人员已领取', '2名主实验员、4工位', 'U12-05', '已DONE的P-02']
    record('current-use corrections', all(s in current for s in expected),
           'Current usage covers timing, route, privacy, staffing, activity qualifications and P-02 status')
    plan = material_dir / '00_第5步计划.md'
    text = plan.read_text(encoding='utf-8')
    target = re.search(r'\[G-01当前使用稿\]\(([^)]+)\)', text)
    record('active entry link', target is not None and (plan.parent / target[1]).resolve()
           == (TASK / 'outputs/current-governance.md').resolve() and '签收DONE' in text,
           'Step-five entry links actual Agent current-use source and signed DONE scope')
    prohibited = re.compile('诊断|治疗|疾病|患者|医疗设备|临床')
    record('current wording', not prohibited.search(current + text), 'Current-use material and entry meet project wording rule')
    commands = [
        ('teaching contract tests', [sys.executable, '-m', 'pytest', '-q',
         str(ROOT / 'agent/tasks/U12-03/execution/test_contract.py')]),
        ('task registry', [sys.executable, str(GOV / '07_validate_task_packages.py')]),
        ('dispatch snapshots', [sys.executable, str(GOV / '14_validate_ready_task_packages.py')]),
    ]
    for name, command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
        record(name, result.returncode == 0, result.stdout.strip() + result.stderr.strip())
    destination = TASK / 'evidence/verification.json'
    report = {'task_id': 'G-01', 'review_date': '2026-09-29',
              'scope': 'Material/current-use alignment only; no new human signature or participant evidence.',
              'checks': checks}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS G-01 current-use verification: {len(checks)} checks')


if __name__ == '__main__':
    main()
