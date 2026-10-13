"""Materialize the already signed evidence branch without modifying its bytes."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
COMMIT = 'ab25a6b8df85c1326164eb8f9f0804d6d790dc87'
PREFIX = '03-测试与实验/evidence/U-02-grip/'


def main():
    names = subprocess.check_output(
        ['git', 'ls-tree', '-rz', '--name-only', COMMIT, '--', PREFIX], cwd=ROOT
    ).decode('utf-8').strip('\0').split('\0')
    if len(names) != 127:
        raise ValueError('U02_HISTORICAL_FILE_COUNT')
    output = PACKAGE / 'archive/evidence-v1'
    for name in names:
        relative = Path(name.removeprefix(PREFIX))
        if not name.startswith(PREFIX) or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('U02_HISTORICAL_PATH')
        content = subprocess.check_output(['git', 'show', f'{COMMIT}:{name}'], cwd=ROOT)
        path = output / relative
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f'U02_HISTORICAL_BYTES_CHANGED:{relative}')
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    (PACKAGE / 'evidence/historical-import.json').write_text(json.dumps({
        'task_id': 'U-02', 'source_commit': COMMIT, 'source_prefix': PREFIX,
        'file_count': len(names), 'byte_comparison': 'PASS',
        'scope': 'Signed historical evidence; not a new run or new signoff'
    }, indent=2) + '\n', encoding='utf-8')
    print('PASS imported and compared 127 signed historical files')


if __name__ == '__main__':
    main()
