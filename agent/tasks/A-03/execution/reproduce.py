"""Reproduce signed synthetic reports in a new directory, never in place."""
import json
from pathlib import Path
import sys
from tempfile import mkdtemp

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
sys.path.insert(0, str(ROOT / '02-技术研发/02-信号处理'))
from a03_gate2_spec.simulation import run_simulation

HISTORY = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析/A-03_SPEC'
CASES = (
    (24, 'sensitivity_point', 'synthetic_small_sample_report_v1.1.json'),
    (85, 'existing_planning_anchor', 'synthetic_planning_anchor_report_v1.1.json'),
    (96, 'complete_target', 'synthetic_complete_target_report_v1.1.json'),
)


def main():
    runtime = TASK / 'evidence/runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    output = Path(mkdtemp(prefix='reproduction-', dir=runtime))
    checks = []
    for per_condition, scope, filename in CASES:
        report = run_simulation(seed=20260906, replications=1000, per_condition=per_condition, decision_scope=scope)
        with (output / filename).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        original = json.loads((HISTORY / filename).read_text(encoding='utf-8-sig'))
        checks.append({'per_condition': per_condition, 'matches_signed_json': report == original,
                       'decision': report['decision'], 'target_joint': report['scenarios']['target']['BOTH_ANALYSIS_SETS']['joint_pass_probability']})
        print(json.dumps(checks[-1]), flush=True)
    with (output / 'comparison.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps({'task_id': 'A-03', 'evidence_class': 'SYNTHETIC_ONLY', 'checks': checks}, indent=2) + '\n')
    print(output)
    return int(any(not check['matches_signed_json'] for check in checks))


if __name__ == '__main__':
    sys.exit(main())
