"""Physically relocate design, validation and reference sources and current consumers."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
MOVES = {'01-需求与设计': 'agent/design', '03-测试与实验': 'agent/validation',
         'srp参考文献': 'agent/references'}
EVIDENCE = ROOT / 'agent/evidence'
ORIGINALS = EVIDENCE / 'root-migration-support-originals.json'
REPAIRS = EVIDENCE / 'root-migration-support-repairs.json'
SCOPE = 'support'


def configure(scope):
    global MOVES, ORIGINALS, REPAIRS, SCOPE
    SCOPE = scope
    if scope == 'modules':
        MOVES = {'agent/modules': 'agent/modules'}
        ORIGINALS = EVIDENCE / 'root-migration-modules-originals.json'
        REPAIRS = EVIDENCE / 'root-migration-modules-repairs.json'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def relocate(relative):
    for old, new in MOVES.items():
        if relative == old or relative.startswith(old + '/'):
            return new + relative[len(old):]
    return relative


def tracked():
    return [p.decode('utf-8') for p in subprocess.check_output(
        ['git', 'ls-files', '-z'], cwd=ROOT).split(b'\0') if p]


def current(relative):
    return not any(part in '/' + relative for part in (
        '/archive/', '/sources/', '/baseline/', '/external_source/', '/90_既有执行材料/',
        '/当前解锁独立任务包/', '/acceptance/', '/evidence/',
    ))


def capture():
    if ORIGINALS.exists():
        raise ValueError('Original capture already exists')
    entries = [{'old': p, 'new': relocate(p),
                'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}
               for p in tracked() if relocate(p) != p]
    save(ORIGINALS, {'baseline_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(), 'files': entries})
    if SCOPE == 'modules':
        bindings = []
        for manifest in (ROOT / 'agent/governance').glob('**/当前解锁独立任务包/*/package_manifest.json'):
            data = json.loads(manifest.read_text(encoding='utf-8-sig'))
            for item in data['source_files']:
                relative = item['source_path']
                if relocate(relative) == relative or not (ROOT / relative).is_file():
                    continue
                preserved = 'agent/archive/root-migration/modules-inputs/' + relative.split('/', 1)[1]
                destination = ROOT / preserved
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
                bindings.append({'task_id': data['task_id'], 'old_project_path': relative,
                                 'new_project_path': preserved,
                                 'preserve_ready_dispatch': True,
                                 'impact_path': 'agent/evidence/root-migration-modules-impact.md',
                                 'reason': 'Preserve dispatch input bytes while relocating current shared runtime code.'})
        save(EVIDENCE / 'root-migration-modules-inputs.json', {'bindings': bindings})
    print(f'CAPTURED {len(entries)} original files')


def rewrite_links(text, old_path, new_path):
    def replace(match):
        location, separator, fragment = match.group(1).partition('#')
        if location.startswith(('http:', 'https:', 'mailto:')) or not location:
            return match.group(0)
        original = (old_path.parent / unquote(location)).resolve()
        if not original.is_relative_to(ROOT):
            return match.group(0)
        target = ROOT / relocate(original.relative_to(ROOT).as_posix())
        if not target.exists():
            return match.group(0)
        if old_path == new_path and target == original:
            return match.group(0)
        relative = os.path.relpath(target, new_path.parent).replace('\\', '/')
        return '](' + relative + (separator + fragment if separator else '') + ')'
    return re.sub(r'\]\(([^)]+)\)', replace, text)


def repair():
    changed = []
    for relative in tracked():
        path = ROOT / relocate(relative)
        if not path.is_file() or not current(relative):
            continue
        code = path.suffix in {'.py', '.ps1', '.cs'} and relative != 'agent/tasks/U-02/execution/import_historical.py'
        doc = path.suffix == '.md' and (
            path.name == 'README.md' or relative in {'AGENTS.md', 'human/project/PROJECT_MODULES.md'}
            or relative.startswith('agent/tasks/')
        )
        if relative.startswith('03-测试与实验/') and path.name != 'README.md':
            continue
        if code or doc:
            before = path.read_bytes()
            text = before.decode('utf-8-sig')
            if doc:
                text = rewrite_links(text, ROOT / relative, path)
            for old, new in MOVES.items():
                text = text.replace(old + '/', new + '/').replace(old + '\\', new.replace('/', '\\') + '\\')
                if path.suffix != '.cs':
                    for quote in ('"', "'"):
                        text = text.replace(quote + old + quote, quote + new + quote)
            encoded = (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
            if encoded != before:
                path.write_bytes(encoded)
                changed.append(path.relative_to(ROOT).as_posix())
    for task in (ROOT / 'agent/tasks').iterdir():
        for name in ('inputs/sources.json', 'outputs/summary.json'):
            path = task / name
            content = json.loads(path.read_text(encoding='utf-8-sig'))
            before = json.dumps(content, ensure_ascii=False)
            if name.startswith('inputs'):
                content['paths'] = [relocate(p) for p in content['paths']]
            else:
                for source in content.get('source_links', []):
                    source['path'] = relocate(source['path'])
            if json.dumps(content, ensure_ascii=False) != before:
                save(path, content)
                changed.append(path.relative_to(ROOT).as_posix())
    words = []
    for path in sorted((ROOT / 'human/tasks').glob('*/summary.docx')):
        output = io.BytesIO()
        count = 0
        with ZipFile(path) as source, ZipFile(output, 'w') as destination:
            for member in source.infolist():
                content = source.read(member.filename)
                if member.filename == 'word/_rels/document.xml.rels':
                    xml = etree.fromstring(content)
                    for rel in xml:
                        target = rel.get('Target', '')
                        if not target.startswith('file:'):
                            continue
                        actual = Path(unquote(urlsplit(target).path).lstrip('/'))
                        if actual.is_relative_to(ROOT):
                            relative = actual.relative_to(ROOT).as_posix()
                            new = relocate(relative)
                            if new != relative:
                                rel.set('Target', (ROOT / new).as_uri())
                                count += 1
                    if count:
                        content = etree.tostring(xml, xml_declaration=True, encoding='UTF-8', standalone=True)
                destination.writestr(member, content)
        if count:
            path.write_bytes(output.getvalue())
            words.append({'path': path.relative_to(ROOT).as_posix(), 'links': count})
    save(REPAIRS, {'current_files_repaired': changed, 'word_relationships_repaired': words})
    if SCOPE == 'modules':
        mapping = ROOT / 'agent/normalization-relocations.json'
        content = json.loads(mapping.read_text(encoding='utf-8'))
        for binding in json.loads((EVIDENCE / 'root-migration-modules-inputs.json').read_text(encoding='utf-8'))['bindings']:
            if (ROOT / relocate(binding['old_project_path'])).read_bytes() != (ROOT / binding['new_project_path']).read_bytes():
                if binding not in content['frozen_sources']:
                    content['frozen_sources'].append(binding)
        save(mapping, content)
    print(f'REPAIRED {len(changed)} current consumers, {len(words)} Word relationship parts')


def verify():
    original = json.loads(ORIGINALS.read_text(encoding='utf-8'))
    repair = json.loads(REPAIRS.read_text(encoding='utf-8'))
    changed = set(repair['current_files_repaired']) | {'agent/design/README.md'}
    if SCOPE == 'modules':
        manual = EVIDENCE / 'root-migration-modules-manual.json'
        if manual.exists():
            changed.update(json.loads(manual.read_text(encoding='utf-8'))['files'])
    unchanged = 0
    for item in original['files']:
        path = ROOT / item['new']
        if (ROOT / item['old']).exists() or not path.is_file():
            raise ValueError('Not a physical move: ' + item['old'])
        same = hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        if not same and item['new'] not in changed:
            raise ValueError('Undocumented original mutation: ' + item['new'])
        if item['old'].startswith('03-测试与实验/') and path.name != 'README.md' and not same:
            raise ValueError('Historical validation bytes changed: ' + item['new'])
        unchanged += same
    revised_words = 0
    for item in repair['word_relationships_repaired']:
        from verify_summary_refresh import verify_refreshed_word
        revised = verify_refreshed_word(item['path'])
        revised_words += revised
        before = subprocess.check_output(['git', 'show', original['baseline_commit'] + ':' + item['path']], cwd=ROOT)
        with ZipFile(io.BytesIO(before)) as previous, ZipFile(ROOT / item['path']) as current_word:
            assert previous.namelist() == current_word.namelist()
            for name in previous.namelist():
                allowed_parts = {'word/_rels/document.xml.rels'} | ({'word/document.xml'} if revised else set())
                if name not in allowed_parts:
                    assert previous.read(name) == current_word.read(name), (item['path'], name)
    result = {'original_files': len(original['files']), 'unchanged_original_files': unchanged,
              'word_documents_checked': len(repair['word_relationships_repaired']),
              'word_documents_link_only': len(repair['word_relationships_repaired']) - revised_words,
              'current_summary_word_revisions_verified': revised_words,
              'word_hyperlinks_relocated': sum(x['links'] for x in repair['word_relationships_repaired']),
              'historical_validation_and_reference_sources_preserved': True,
              'scope': 'Physical support root moves and current links, not new acceptance'}
    save(EVIDENCE / f'root-migration-{SCOPE}-preservation.json', result)
    print('PASS', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'repair', 'verify'])
    parser.add_argument('--scope', choices=['support', 'modules'], default='support')
    args = parser.parse_args()
    configure(args.scope)
    {'capture': capture, 'repair': repair, 'verify': verify}[args.action]()
