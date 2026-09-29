"""Check real root moves and current human/Agent links without business signoff."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from docx import Document

from build_task_reviews import check_task

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def check_markdown(path):
    count = 0
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
        if link.startswith(('https://', 'http://', '#')):
            continue
        target = path.parent / unquote(link.split('#')[0])
        if not target.resolve().exists():
            raise ValueError(f'Missing current link: {path.relative_to(ROOT)} -> {link}')
        count += 1
    return count


def check_word(task_id, summary):
    path = ROOT / f'human/tasks/{task_id}/summary.docx'
    doc = Document(path)
    text = '\n'.join(p.text for p in doc.paragraphs)
    expected = [summary['conclusion']]
    expected.extend(p for s in summary['sections'] for p in s['paragraphs'])
    if any(p not in text for p in expected):
        raise ValueError(f'Word content does not match Agent source: {task_id}')
    count = 0
    for rel in doc.part.rels.values():
        if not rel.is_external or not rel.target_ref.startswith('file:'):
            continue
        value = unquote(urlsplit(rel.target_ref).path)
        if re.match(r'^/[A-Za-z]:/', value):
            value = value[1:]
        if not Path(value).exists():
            raise ValueError(f'Missing Word source: {task_id} -> {value}')
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    layout = read(ROOT / 'agent/root-layout.json')
    migrated = []
    pending = []
    for entry in layout['entries']:
        if entry['status'] != 'MIGRATED':
            pending.append(entry['old'])
            continue
        if (ROOT / entry['old']).exists() or not (ROOT / entry['new']).exists():
            raise ValueError(f'Migration not physical: {entry["old"]}')
        if entry.get('original_byte_sha256'):
            digest = hashlib.sha256((ROOT / entry['new']).read_bytes()).hexdigest().upper()
            if digest != entry['original_byte_sha256']:
                raise ValueError(f'Historical original changed: {entry["old"]}')
        migrated.append(entry['old'])
    with (GOV / '05_可领取任务包.csv').open(encoding='utf-8-sig', newline='') as stream:
        registry = {row['task_id']: row for row in csv.DictReader(stream)}
    word_links = 0
    for task_id in registry:
        summary = check_task(task_id, registry)
        word_links += check_word(task_id, summary)
    current_paths = ['human/project/README.md', 'human/project/PROJECT_MODULES.md',
                     'agent/runtime/README.md', 'agent/archive/project/README.md',
                     'agent/archive/runtime/README.md', 'README.md', 'human/README.md',
                     'human/deliverables/README.md', 'human/deliverables/archive/README.md',
                     'agent/archive/delivery/README.md', '04-成果与交付/README.md',
                     '04-成果与交付/PDF简报/README.md']
    markdown_links = sum(check_markdown(ROOT / path) for path in current_paths)
    unexpected = sorted(p.name for p in ROOT.iterdir() if p.name not in layout['root_entries_retained'])
    if args.require_complete and (pending or unexpected or not layout['root_migration_complete']):
        raise ValueError(f'Overall migration incomplete: pending={pending}, root={unexpected}')
    result = {'scope': 'Physical completed moves and all current task/Word source links; not Unity/TD runtime or business acceptance',
              'migrated_roots': migrated, 'pending_roots': pending,
              'task_packages_checked': len(registry), 'word_source_links_checked': word_links,
              'current_markdown_links_checked': markdown_links,
              'root_entries_still_to_classify': unexpected,
              'root_migration_complete': layout['root_migration_complete']}
    (ROOT / 'agent/evidence/root-migration-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS {len(migrated)} physical moves, {len(registry)} packages and {word_links} Word source links; {len(pending)} root moves pending')


if __name__ == '__main__':
    main()
