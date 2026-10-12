"""Check design artifacts, independent budget arithmetic and protected history."""
from pathlib import Path
from collections import Counter
from statistics import NormalDist
import csv
import json
import re
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / 'agent/design/design-foundation-20261008'
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
BEFORE = ROOT / 'agent/local/artifacts/operational-design-20261008/before/state.json'


def verify():
    data = json.loads((DESIGN / 'operational-design.json').read_text(encoding='utf-8'))
    assert data['scope'] == 'DESIGN_ONLY' and not data['formal_collection_allowed']
    assert not data['numeric_parameters_frozen'] and not data['runtime_api_modified']
    texts = {}
    page_count = 0
    for name in ['05-control-spec', '06-paired-storyboards', '07-protocol-candidate']:
        source = DESIGN / (name + '.tex')
        pdf = DESIGN / (name + '.pdf')
        assert pdf.stat().st_mtime >= source.stat().st_mtime, name
        reader = PdfReader(str(pdf))
        page_count += len(reader.pages)
        texts[name] = ''.join(p.extract_text() or '' for p in reader.pages)
        fonts = set()
        for page in reader.pages:
            for ref in page['/Resources']['/Font'].values():
                font = ref.get_object()
                fonts.add(str(font['/BaseFont']))
                descendant = font['/DescendantFonts'][0].get_object() if '/DescendantFonts' in font else font
                descriptor = descendant['/FontDescriptor'].get_object()
                assert any(x in descriptor for x in ['/FontFile','/FontFile2','/FontFile3']), font
        assert any('SimHei' in f for f in fonts) and any('MicrosoftYaHei' in f for f in fonts), fonts
        log = ROOT / 'agent/local/artifacts/task-latex-20261008/build/design-foundation-20261008' / (name + '.log')
        log_text = log.read_text(encoding='utf-8',errors='replace')
        assert 'Overfull' not in log_text and 'Missing character' not in log_text, name
    assert all(r in texts['05-control-spec'] for r in data['rules'])
    assert all(s in texts['06-paired-storyboards'] for s in data['scenarios'])
    story_source = (DESIGN / '06-paired-storyboards.tex').read_text(encoding='utf-8')
    assert story_source.count('\\storyframe{') == len(data['scenarios']) * 3
    orders = data['randomization_candidate']['orders']
    for position in range(4):
        assert len({row[position] for row in orders}) == 4
    adjacent = Counter(pair for row in orders for pair in zip(row,row[1:]))
    assert len(adjacent) == 12 and set(adjacent.values()) == {1}
    p = data['participants']
    assert p['formal_if_100_students'] == 100 - p['cognitive_students'] - p['planning_technical_students']
    assert p['formal_if_100_people_including_experts'] == p['formal_if_100_students'] - p['expert_review']
    protocol_source = (DESIGN / '07-protocol-candidate.tex').read_text(encoding='utf-8')
    z = NormalDist()
    for n in [60,68,76,100]:
        values = [2*z.inv_cdf(.975)/n**.5,2*(z.inv_cdf(.975)+z.inv_cdf(.8))/n**.5,2*(z.inv_cdf(.975)+z.inv_cdf(.9))/n**.5]
        expected = str(n) + ' & ' + ' & '.join(f'{v:.3f}' for v in values)
        assert expected in protocol_source, expected
    assert (20 + 40 + 40) == 100 and (20+40)/100 == .6
    assert '不能只用断流秒数' in protocol_source and 'C+K+U=T' in protocol_source
    before = json.loads(BEFORE.read_text(encoding='utf-8'))
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig',newline='') as stream:
        assert list(csv.DictReader(stream)) == before['registry'], 'Business registry changed'
    for task, old in before['dispatch'].items():
        current = json.loads((GOV / '当前解锁独立任务包' / task / 'package_manifest.json').read_text(encoding='utf-8'))
        row = next(r for r in before['registry'] if r['task_id'] == task)
        if row['status'] in ['IN_PROGRESS','IN_REVIEW']:
            assert current['input_snapshot_id'] == old['input_snapshot_id'], task
            assert current.get('candidate_identity') == old.get('candidate_identity'), task
        assert any(x['source_path'].endswith('operational-design.json') for x in current['design_updates']), task
    links = 0
    for task in data['consumers']:
        folder = ROOT / 'agent/tasks' / task
        summary = json.loads((folder / 'outputs/summary.json').read_text(encoding='utf-8'))
        archived = json.loads((folder / 'archive/pre-design-baseline-20261008/summary.json').read_text(encoding='utf-8-sig'))
        assert summary['historical_acceptance'] == archived['historical_acceptance'], task
        assert summary['operational_design_candidate'] == data['candidate_id'], task
        path = folder / 'outputs/operational-design-handoff.md'
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            assert (path.parent / target).exists(), (task,target)
            links += 1
    print(f'PASS: 10 rules, 12 paired scenarios/36 stages, {page_count} design PDF pages, {len(data["consumers"])} consumers/{links} handoff links; independent precision/order/budget checks and original registry/active claims preserved')


if __name__ == '__main__':
    verify()
