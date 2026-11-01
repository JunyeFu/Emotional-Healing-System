"""Run bounded six-family benefit/null/harm/floor software scenarios."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'agent/modules'))
from srp_analysis.demo import make_demo
from srp_analysis.prepare import prepare
from srp_analysis.analyze import analyze
from srp_analysis.io import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cases = []
    expected = {'benefit': 'B_LOWER', 'null': 'DIRECTION_UNCERTAIN', 'harm': 'A_LOWER'}
    for scenario in ('benefit', 'null', 'harm', 'floor'):
        root = args.out / scenario
        root.mkdir()
        bundle = make_demo(root / 'originals', n=30, scenario=scenario)
        prepared = prepare(bundle, root / 'prepared')
        output = analyze(prepared, root / 'results')
        value = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))
        primary = value['primary']
        assert primary['n'] == 30 and primary['status'] == 'ESTIMATED'
        if scenario in expected:
            assert primary['interpretation'].startswith(expected[scenario]), (scenario, primary)
        cases.append(dict(scenario=scenario, primary=primary, report=str(output / 'report.pdf')))
        print(f"PASS {scenario}: {primary['interpretation']}", flush=True)
    write_json(args.out / 'software-scenarios.json', dict(evidence_class='SYNTHETIC',
               real_device_validation='NOT_RUN', research_acceptance='NOT_RUN', cases=cases))


if __name__ == '__main__':
    main()
