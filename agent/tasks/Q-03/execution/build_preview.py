"""Describe 48 design cells, not a randomized list or runnable manifest."""
import argparse
from itertools import permutations
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]


def preview():
    cells = []
    for sequence in permutations(('storm', 'heat', 'snow', 'fade')):
        for condition in ('scene_native', 'abstract_pacer'):
            index = len(cells) + 1
            cells.append({'design_cell': index, 'capacity_batch': (index - 1) // 12 + 1,
                          'condition': condition, 'weather_sequence': list(sequence)})
    return {'scope': 'DESIGN_CELLS_ONLY_NOT_ALLOCATION_OR_MANIFEST',
            'formal_capable': False, 'randomized': False, 'participants_observed': 0,
            'cells': cells}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = TASK / 'outputs/design-cell-preview.json'
    encoded = json.dumps(preview(), ensure_ascii=False, indent=2) + '\n'
    if args.check or path.exists():
        if path.read_text(encoding='utf-8') != encoded:
            raise ValueError('DESIGN_CELL_PREVIEW_DRIFT')
    else:
        with path.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(encoded)
    print('PASS: 48 design cells; not randomized allocation, session manifests or real evidence')


if __name__ == '__main__':
    main()
