"""Current identities only; never rewrite the signed evidence bundle."""
import argparse
import hashlib
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]


def text_hash(path):
    text = path.read_text(encoding='utf-8-sig')
    normalized = '\n'.join(line.rstrip() for line in text.splitlines()) + '\n'
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest().upper()


def generate():
    sources = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))['paths']
    outputs = [
        'outputs/contract.json', 'outputs/sap.md', 'outputs/power_spec.json',
        'outputs/current-statistics.md', 'outputs/current-statistics.json',
        'outputs/parameter-sources.md', 'outputs/power/power_grid.json', 'outputs/power/power_report.md',
        'execution/power_simulation.py', 'execution/validate.py', 'execution/test_contract.py',
    ]
    old = json.loads((TASK / 'archive/signed-candidate/evidence.json').read_text(encoding='utf-8'))
    return {
        'task_id': 'U12-04', 'evidence_class': 'DESIGN_AND_SYNTHETIC_ONLY',
        'hash_policy': 'UTF8_LF_TRAILING_WHITESPACE_REMOVED_FINAL_LF',
        'historical_candidate': 'd701a4054a4a36030d37335efa65d67a93ed35c3',
        'historical_input_snapshot_id': old['input_snapshot_id'],
        'sources': {p: text_hash(ROOT / p) for p in sources},
        'outputs': {p: text_hash(TASK / p) for p in outputs},
        'research_freeze': 'PENDING', 'real_data_analysis': 'NOT_RUN',
        'new_human_acceptance': 'NOT_SIGNED',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = TASK / 'evidence/current-design.json'
    content = json.dumps(generate(), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if path.read_text(encoding='utf-8') != content:
            raise SystemExit('EVIDENCE_MISMATCH')
        print('PASS current identities; original signed evidence unchanged')
    else:
        path.write_text(content, encoding='utf-8')
        print('WROTE evidence/current-design.json')


if __name__ == '__main__':
    main()
