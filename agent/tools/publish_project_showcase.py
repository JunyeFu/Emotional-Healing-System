"""Publish only reader-facing files to main, linking code to a fixed full revision."""

import argparse
import os
from pathlib import Path
import posixpath
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REPO = 'https://github.com/JunyeFu/Emotional-Healing-System'
PAGES = [
    'README.md', 'CONTRIBUTING.md', 'human/README.md',
    'human/project/README.md', 'human/project/PROJECT_MODULES.md',
    'human/project/project-introduction.md', 'human/project/repository-layout.md',
    'human/project/repository-restructure-taskbook-20261013.md',
    'human/developers/README.md', 'human/tasks/README.md', 'human/deliverables/README.md',
]
ASSETS = ['human/assets/readme/team-task-progress.svg'] + [
    f'human/assets/previews/2026-10-08/member-storm-particle-rings/{name}'
    for name in ('README.md', 'frame-index.json', 'video-01-t12.png',
                 'video-01-t20.png', 'video-02-t05.png', 'video-02-t26.png', 'video-02-t42.png')
]


def git(*args, data=None, env=None):
    return subprocess.check_output(['git', *args], cwd=ROOT, input=data, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args()
    source = git('rev-parse', args.source).decode().strip()
    base = git('rev-parse', args.base).decode().strip()
    selected = set(PAGES + ASSETS)
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / 'index'))
        git('read-tree', '--empty', env=env)
        # Preserve the old default branch under one explicit historical location.
        legacy = 'agent/archive/default-branch-legacy/'
        entries = git('ls-tree', '-rz', base).split(b'\0')
        already_archived = any(b'\t' + legacy.encode('utf-8') in entry for entry in entries)
        archived = []
        for entry in entries:
            if not entry:
                continue
            metadata, name_bytes = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            name = name_bytes.decode('utf-8')
            if already_archived:
                if name.startswith(legacy):
                    archived.append(f'{mode} {oid}\t{name}'.encode('utf-8'))
                continue
            if name in selected:
                continue
            archived.append(f'{mode} {oid}\t{legacy}{name}'.encode('utf-8'))
        git('update-index', '-z', '--index-info',
            data=b'\0'.join(archived) + b'\0', env=env)
        generated = {
            'agent/README.md': f'# Agent source navigation\n\nCurrent implementation: [full normalized project]({REPO}/tree/{source}/agent).\n\nThe default branch is the project showcase. Its previous implementation is preserved under [default-branch-legacy](archive/default-branch-legacy/README.md), not an active runtime entry.\n',
            'agent/archive/default-branch-legacy/README.md': f'# Archived default-branch implementation\n\nOriginal default-branch revision: [{base[:8]}]({REPO}/tree/{base}). Files are preserved unchanged under this directory; relative runtime paths belong to that original revision. Use the original revision to reproduce it.\n\nCurrent normalized implementation: [{source[:8]}]({REPO}/tree/{source}). This archive does not merge newer implementation into main.\n',
            '.gitattributes': '*.png filter=lfs diff=lfs merge=lfs -text\n*.pdf filter=lfs diff=lfs merge=lfs -text\n*.toe filter=lfs diff=lfs merge=lfs -text\n*.zip filter=lfs diff=lfs merge=lfs -text\n',
        }
        if already_archived:
            generated.pop(legacy + 'README.md')
        for name, body in generated.items():
            oid = git('hash-object', '-w', '--stdin', data=body.encode('utf-8')).decode().strip()
            git('update-index', '--add', '--cacheinfo', f'100644,{oid},{name}', env=env)
        for name in PAGES + ASSETS:
            data = git('show', f'{source}:{name}')
            if name.endswith('.md'):
                body = data.decode('utf-8')

                def link(match):
                    prefix, target = match.groups()
                    if target.startswith(('https:', 'http:', '#', 'mailto:')):
                        return match.group(0)
                    path, _, anchor = target.strip('<>').partition('#')
                    path = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
                    if path in selected:
                        return match.group(0)
                    route = 'raw' if prefix.startswith('!') else 'blob'
                    url = f'{REPO}/{route}/{source}/{path}'
                    return f'{prefix}({url}' + (f'#{anchor}' if anchor else '') + ')'

                body = re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)', link, body)
                if name == 'README.md':
                    first, rest = body.split('\n', 1)
                    body = first + f'\n\n完整规范化项目版本：[{source[:8]}]({REPO}/tree/{source})，2026-10-13发布。main同步展示与开发导航，运行实现保留在工作分支。\n' + rest
                data = body.encode('utf-8')
            oid = git('hash-object', '-w', '--stdin', data=data).decode().strip()
            git('update-index', '--add', '--cacheinfo', f'100644,{oid},{name}', env=env)
        tree = git('write-tree', env=env).decode().strip()
        commit = git('commit-tree', tree, '-p', base, '-m',
                     f'docs: showcase normalized SRP project {source[:8]}').decode().strip()
    print(f'SHOWCASE_COMMIT {commit}; FULL_SOURCE {source}; FILES {len(selected)}')
    if args.push:
        subprocess.run(['git', '-c', 'credential.helper=!gh auth git-credential',
                        'push', REPO + '.git', f'{commit}:refs/heads/main'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
