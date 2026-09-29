"""Recheck accepted media without rewriting accepted evidence."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
REPO = TASK.parents[2]
SOURCE = REPO / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/20_产品与场景设计/V-04_完整分镜与真实时长声音预演'
ARCHIVE = TASK / 'archive/tools'
RUNTIME = TASK / 'evidence/runtime'
CHECKS = (
    'validate_v04_h1', 'validate_v04_h2_v11',
    'validate_v04_h3_storm_v2', 'validate_v04_h3_heat_v2',
    'validate_v04_h3_snow_v2', 'validate_v04_h3_corridor',
    'validate_v04_h3_fixed_combined_review_v2',
    'validate_v04_full_duration_animatic',
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def bind_toolchain():
    lock = json.loads((SOURCE / 'V-04_toolchain-lock_v1.0.json').read_text(encoding='utf-8'))
    tools = REPO / '.tools/ffmpeg/9.0.1/ffmpeg-9.0.1-essentials_build/bin'
    for name in ('ffmpeg', 'ffprobe'):
        path = tools / f'{name}.exe'
        assert sha256(path) == lock['ffmpeg'][f'{name}_executable_sha256'], name
        lock['ffmpeg'][f'{name}_executable'] = str(path)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    target = RUNTIME / 'toolchain-bindings.json'
    target.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target


def bind_module(module, lock_path):
    # Archived modules retain historical filenames; only this entry selects current versions.
    for name, value in list(vars(module).items()):
        if isinstance(value, Path) and value.parent == ARCHIVE:
            setattr(module, name, SOURCE / value.name)
    module.HERE = SOURCE
    module.REPO = REPO
    if hasattr(module, 'LOCK_PATH'):
        module.LOCK_PATH = lock_path
    if module.__name__ == 'validate_v04_full_duration_animatic':
        module.REPORT = RUNTIME / 'full-duration-deep-check.json'


def validate_lfs_entry(entry, root=REPO):
    path = root / entry['name']
    assert path.stat().st_size == entry['size'], f'LFS size: {path}'
    assert sha256(path) == entry['oid'], f'LFS bytes: {path}'


def validate_media_tracking(*paths):
    tracked = subprocess.check_output(['git', 'ls-files', '--', *paths], cwd=REPO,
                                      text=True, encoding='utf-8').splitlines()
    entries = json.loads(subprocess.check_output(['git', 'lfs', 'ls-files', '--json'], cwd=REPO,
                                                 text=True, encoding='utf-8'))['files']
    by_name = {entry['name']: entry for entry in entries}
    for name in tracked:
        assert name in by_name, f'Tracked non-LFS local file: {name}'
        validate_lfs_entry(by_name[name])
    return len(tracked)


def check(name):
    if name not in CHECKS:
        raise ValueError(name)
    lock_path = bind_toolchain()
    sys.path.insert(0, str(ARCHIVE))
    module = importlib.import_module(name)
    for imported in list(sys.modules.values()):
        file = getattr(imported, '__file__', None)
        if file and Path(file).parent == ARCHIVE:
            bind_module(imported, lock_path)
    if hasattr(module, 'implementation'):
        module.implementation.main()
    else:
        module.main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('check', choices=CHECKS)
    check(parser.parse_args().check)
