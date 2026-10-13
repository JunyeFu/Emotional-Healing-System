"""Materialize fixed synthetic cases, not a real-data analysis entry."""
import json
from pathlib import Path

from result_classifier import Evidence, classify

TASK = Path(__file__).resolve().parents[1]


def report():
    source = json.loads((TASK / 'inputs/classifier-cases.json').read_text(encoding='utf-8-sig'))
    return {'scope': source['scope'], 'real_analysis': 'NOT_RUN', 'formal_authorization': False,
            'cases': [{'id': row['id'], 'result': classify(Evidence(**row['evidence']))}
                      for row in source['cases']]}


if __name__ == '__main__':
    path = TASK / 'outputs/synthetic-classification.json'
    path.write_text(json.dumps(report(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'WROTE {len(report()["cases"])} synthetic cases; no real results')
