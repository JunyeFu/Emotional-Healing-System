"""Verify that refreshed Words change normalization facts, not business acceptance."""
import io
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

from docx import Document

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / 'agent/evidence/normalization-summary-refresh.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify_refreshed_word(relative):
    if not REPORT.exists():
        return False
    report = read(REPORT)
    task_id = Path(relative).parent.name
    if not any(entry['task_id'] == task_id for entry in report['summaries']):
        return False
    summary_path = f'agent/tasks/{task_id}/outputs/summary.json'
    before = json.loads(subprocess.check_output(['git', 'show', report['baseline_commit'] + ':' + summary_path], cwd=ROOT))
    after = read(ROOT / summary_path)
    for key in before.keys() - {'sections', 'findings', 'next_task'}:
        assert before[key] == after[key], (task_id, 'Business or acceptance field changed', key)
    assert len(before['sections']) == len(after['sections'])
    for old, new in zip(before['sections'], after['sections']):
        assert old['heading'] == new['heading']
        if old['heading'] not in {'目录与文件整理', '收尾与下一包'}:
            assert old == new, (task_id, 'Business section changed', old['heading'])
    assert len(before['findings']) == len(after['findings'])
    for old, new in zip(before['findings'], after['findings']):
        assert old['id'] == new['id']
        if old['status'] in {'OPEN_ROOT_MIGRATION', 'OPEN_PROJECT_MIGRATION'}:
            assert new['status'] == 'FIXED_PHYSICAL_ROOT_MIGRATION_AND_RUNTIME_CHECKS'
        else:
            assert old['status'] == new['status'] and old['description'] == new['description']
    doc = Document(ROOT / relative)
    text = '\n'.join(p.text for p in doc.paragraphs)
    expected = [after['conclusion'], after['historical_acceptance']['method']]
    expected.extend(p for section in after['sections'] for p in section['paragraphs'])
    assert all(p in text for p in expected), (task_id, 'Word does not match Agent source')
    baseline = subprocess.check_output(['git', 'show', report['baseline_commit'] + ':' + relative], cwd=ROOT)
    with ZipFile(io.BytesIO(baseline)) as old, ZipFile(ROOT / relative) as new:
        assert set(old.namelist()) == set(new.namelist())
        for name in old.namelist():
            if name not in {'word/document.xml', 'word/_rels/document.xml.rels'}:
                assert old.read(name) == new.read(name), (task_id, 'Unrelated Word part changed', name)
    return True


def main():
    report = read(REPORT)
    assert len(report['summaries']) == 71
    for entry in report['summaries']:
        assert verify_refreshed_word(f"human/tasks/{entry['task_id']}/summary.docx")
    result = {'summaries_checked': 71, 'business_conclusions_and_historical_acceptance_preserved': True,
              'business_sections_preserved': True, 'word_bodies_match_current_agent_sources': True,
              'unrelated_word_parts_preserved': True,
              'migration_findings_closed': len(report['migration_findings_closed']),
              'visual_inspection': 'Separate rendered-page record; not inferred from text verification'}
    (ROOT / 'agent/evidence/normalization-summary-check.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS 71 Word sources, business conclusions, historical acceptance and unrelated Word parts')


if __name__ == '__main__':
    main()
