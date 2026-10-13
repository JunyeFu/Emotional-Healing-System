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
        git('read-tree', base, env=env)
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
