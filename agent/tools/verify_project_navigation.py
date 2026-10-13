"""Check the public reading paths without running native project editors."""

from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
PAGES = (
    'README.md', 'CONTRIBUTING.md', 'human/README.md',
    'human/project/README.md', 'human/project/project-introduction.md',
    'human/project/repository-layout.md',
    'human/project/repository-restructure-taskbook-20261013.md',
    'human/developers/README.md', 'human/tasks/README.md',
    'human/deliverables/README.md', 'agent/README.md', 'agent/runtime/README.md',
)


def main():
    checked = 0
    errors = []
    for name in PAGES:
        path = ROOT / name
        body = path.read_text(encoding='utf-8')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', body):
            target = target.strip().strip('<>')
            if target.startswith(('https:', 'http:', '#', 'mailto:')):
                continue
            target = re.sub(r':\d+$', '', unquote(target.split('#')[0]))
            if not (path.parent / target).exists():
                errors.append(f'{name}: {target}')
            checked += 1
    assert len((ROOT / 'README.md').read_text(encoding='utf-8').splitlines()) <= 150
    index = (ROOT / 'human/tasks/README.md').read_text(encoding='utf-8')
    assert len(set(re.findall(r'\]\(([A-Z0-9]+-\d+)/summary.pdf\)', index))) == 71
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'PASS {len(PAGES)} entry pages, {checked} local links, 71 task reviews, homepage <=150 lines')


if __name__ == '__main__':
    main()
