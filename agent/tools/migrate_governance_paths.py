"""Repair current governance consumers while preserving frozen and signed originals."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from lxml import etree

ROOT = Path(__file__).resolve().parents[2]
OLD = '00-项目管理'
NEW = 'agent/governance'
RECORD = ROOT / 'agent/evidence/root-migration-governance-originals.json'


def tracked():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    return [p.decode('utf-8') for p in result.stdout.split(b'\0') if p]


def relocated(relative):
    return NEW + relative[len(OLD):] if relative == OLD or relative.startswith(OLD + '/') else relative


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def capture():
    if RECORD.exists():
        raise ValueError('Original capture already exists')
    paths = [p for p in tracked() if p.startswith(OLD + '/')]
    save_json(RECORD, {'scope': 'Pre-move bytes of tracked governance sources', 'files': [
        {'old': p, 'new': relocated(p), 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}
        for p in paths
    ]})
    print(f'CAPTURED {len(paths)} tracked files')


def current_governance_file(path):
    value = path.as_posix()
    return not any(part in value for part in (
        '/sources/', '/baseline/', '/external_source/', '/90_既有执行材料/',
        '/当前解锁独立任务包/', '/acceptance/', '/archive/',
    ))


def rewrite_links(content, old_path, new_path):
    def replace(match):
        target = match.group(1)
        if target.startswith(('http:', 'https:', '#', 'mailto:')):
            return match.group(0)
        location, separator, anchor = target.partition('#')
        resolved = (old_path.parent / unquote(location)).resolve()
        if not resolved.is_relative_to(ROOT):
            return match.group(0)
        current = ROOT / relocated(resolved.relative_to(ROOT).as_posix())
        if not current.exists():
            return match.group(0)
        result = os.path.relpath(current, new_path.parent).replace('\\', '/')
        return '](' + result + (separator + anchor if separator else '') + ')'
    return re.sub(r'\]\(([^)]+)\)', replace, content)


def repair():
    changed = []
    for relative in tracked():
        path = ROOT / relocated(relative)
        if not path.is_file():
            continue
        is_governance = relative.startswith(OLD + '/')
        is_task = relative.startswith('agent/tasks/')
        current_code = path.suffix in {'.py', '.ps1'} and (
            (is_governance and current_governance_file(path)) or
            (is_task and '/execution/' in relative) or
            relative.startswith(('agent/tools/governance/', '02-技术研发/tests/', 'agent/delivery/')) or
            relative in {'agent/tools/build_task_reviews.py', 'agent/tools/verify_root_migration.py'}
        )
        current_doc = path.suffix == '.md' and (
            relative in {'README.md', 'AGENTS.md', 'human/README.md', 'agent/README.md',
                         'human/project/README.md', 'human/project/PROJECT_MODULES.md', 'agent/runtime/README.md'} or
            (is_task and '/archive/' not in relative and '/evidence/' not in relative) or
            (is_governance and current_governance_file(path) and
             (path.name == 'README.md' or path.name in {'04_可领取树型任务包_v2.0.md',
              '00_四人团队职责与任务树.md', '当前阶段看板.md'}))
        )
        if current_code or current_doc:
            before = path.read_bytes()
            text = before.decode('utf-8-sig')
            if current_code and relative != 'agent/tasks/F-03/execution/Invoke-F03.ps1':
                text = text.replace(OLD + '/', NEW + '/').replace('"' + OLD + '"', '"' + NEW + '"')
            if current_doc:
                text = rewrite_links(text, ROOT / relative, path)
                if relative in {'README.md', 'AGENTS.md', 'human/project/PROJECT_MODULES.md'}:
                    text = text.replace(OLD + '/', NEW + '/')
            encoded = text.encode('utf-8')
            if before.startswith(b'\xef\xbb\xbf'):
                encoded = b'\xef\xbb\xbf' + encoded
            if encoded != before:
                path.write_bytes(encoded)
                changed.append(path.relative_to(ROOT).as_posix())
    for package in (ROOT / 'agent/tasks').iterdir():
        for name in ('inputs/sources.json', 'outputs/summary.json'):
            path = package / name
            content = json.loads(path.read_text(encoding='utf-8-sig'))
            if name.startswith('inputs'):
                new_values = [relocated(p) for p in content['paths']]
                modified = new_values != content['paths']
                content['paths'] = new_values
            else:
                modified = False
                for link in content.get('source_links', []):
                    value = relocated(link['path'])
                    modified |= value != link['path']
                    link['path'] = value
            if modified:
                save_json(path, content)
                changed.append(path.relative_to(ROOT).as_posix())
    word_changes = []
    for path in sorted((ROOT / 'human/tasks').glob('*/summary.docx')):
        original = path.read_bytes()
        output = io.BytesIO()
        count = 0
        with ZipFile(io.BytesIO(original)) as source, ZipFile(output, 'w') as destination:
            for item in source.infolist():
                content = source.read(item.filename)
                if item.filename == 'word/_rels/document.xml.rels':
                    xml = etree.fromstring(content)
                    for rel in xml:
                        target = rel.get('Target', '')
                        if not target.startswith('file:'):
                            continue
                        value = unquote(urlsplit(target).path).lstrip('/')
                        actual = Path(value)
                        if not actual.is_relative_to(ROOT):
                            continue
                        relative = actual.relative_to(ROOT).as_posix()
                        new = relocated(relative)
                        if new != relative:
                            rel.set('Target', (ROOT / new).as_uri())
                            count += 1
                    if count:
                        content = etree.tostring(xml, xml_declaration=True, encoding='UTF-8', standalone=True)
                destination.writestr(item, content)
        if count:
            path.write_bytes(output.getvalue())
            word_changes.append({'path': path.relative_to(ROOT).as_posix(), 'links': count,
                                 'body_unchanged': True})
    save_json(ROOT / 'agent/evidence/root-migration-governance-repairs.json', {
        'current_files_repaired': changed, 'word_relationships_repaired': word_changes,
        'frozen_or_signed_originals_rewritten': False,
    })
    print(f'REPAIRED {len(changed)} current files; {len(word_changes)} Word relationship parts')


def navigation():
    record = ROOT / 'agent/evidence/root-migration-governance-repairs.json'
    repairs = json.loads(record.read_text(encoding='utf-8'))
    changed = set(repairs['current_files_repaired'])
    count = 0
    for entry in json.loads(RECORD.read_text(encoding='utf-8'))['files']:
        path = ROOT / entry['new']
        if path.name == 'package_manifest.json' and current_governance_file(path):
            manifest = json.loads(path.read_text(encoding='utf-8-sig'))
            if manifest.get('package_role') == 'LEGACY_NAVIGATION_ONLY' and entry['new'] not in changed:
                for key, value in manifest.items():
                    if isinstance(value, str) and value.startswith('../'):
                        resolved = (ROOT / entry['old']).parent / value
                        target = ROOT / relocated(resolved.resolve().relative_to(ROOT).as_posix())
                        if not target.exists():
                            raise ValueError('Missing navigation target: ' + str(target))
                        manifest[key] = os.path.relpath(target, path.parent).replace('\\', '/')
                save_json(path, manifest)
                changed.add(entry['new'])
                count += 1
        if path.suffix != '.md' or not current_governance_file(path):
            continue
        if '已签署' in path.name or '第二人审核报告' in path.name:
            continue
        before = path.read_text(encoding='utf-8-sig')
        if 'agent/tasks/' not in before and '/tasks/' not in before:
            continue
        old_parent = path if entry['new'] in changed else ROOT / entry['old']
        content = rewrite_links(before, old_parent, path)

        def canonical(match):
            target = match.group(1)
            if target.startswith(('http:', 'https:', '#', 'mailto:')):
                return match.group(0)
            location, separator, anchor = target.partition('#')
            resolved = (path.parent / unquote(location)).resolve()
            if not resolved.is_relative_to(ROOT / 'agent/tasks') or not resolved.exists():
                return match.group(0)
            relative = os.path.relpath(ROOT, path.parent).replace('\\', '/')
            return '](' + relative + '/' + resolved.relative_to(ROOT).as_posix() + (separator + anchor if separator else '') + ')'

        content = re.sub(r'\]\(([^)]+)\)', canonical, content)
        if content != before:
            bom = b'\xef\xbb\xbf' if path.read_bytes().startswith(b'\xef\xbb\xbf') else b''
            path.write_bytes(bom + content.encode('utf-8'))
            changed.add(entry['new'])
            count += 1
    repairs['current_files_repaired'] = sorted(changed)
    save_json(record, repairs)
    print(f'REPAIRED {count} current navigation files; signed originals excluded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['capture', 'repair', 'navigation'])
    args = parser.parse_args()
    {'capture': capture, 'repair': repair, 'navigation': navigation}[args.action]()
