"""Merge the complete source tree into main without changing the working directory."""

import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REMOTE = 'https://github.com/JunyeFu/Emotional-Healing-System.git'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args()
    source = git('rev-parse', args.source)
    base = git('rev-parse', args.base)
    tree = git('rev-parse', source + '^{tree}')
    commit = git('commit-tree', tree, '-p', base, '-p', source,
                 '-m', 'merge: make normalized SRP the complete main project')
    print(f'MAIN_MERGE {commit}; SOURCE {source}; TREE {tree}', flush=True)
    if args.push:
        subprocess.run(['git', '-c', 'http.version=HTTP/1.1',
                        '-c', 'credential.helper=!gh auth git-credential',
                        'push', REMOTE, f'{commit}:refs/heads/main'],
                       cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
