"""Locate explicitly migrated source originals without changing frozen input IDs."""
import json
from pathlib import Path
import subprocess

LAYOUT = Path(__file__).resolve().parents[1] / 'root-layout.json'


def resolve_project_path(project_root: Path, relative: str) -> Path:
    """Resolve recorded root paths after a physical move, without rewriting originals."""
    path = (project_root / relative).resolve()
    if not path.is_relative_to(project_root):
        return path
    for entry in json.loads(LAYOUT.read_text(encoding='utf-8'))['entries']:
        if entry['status'] != 'MIGRATED':
            continue
        old = project_root / entry['old']
        if path == old or path.is_relative_to(old):
            return project_root / entry['new'] / path.relative_to(old)
    return path


def historical_project_path(project_root: Path, relative: str) -> str:
    """Translate a current root path for queries against pre-migration Git commits."""
    path = project_root / relative
    for entry in json.loads(LAYOUT.read_text(encoding='utf-8'))['entries']:
        if entry['status'] != 'MIGRATED':
            continue
        current = project_root / entry['new']
        if path == current or path.is_relative_to(current):
            return (Path(entry['old']) / path.relative_to(current)).as_posix()
    return relative


def git_source_bytes(project_root: Path, revision: str, relative: str) -> bytes:
    """Read the same file from a commit on either side of the physical move."""
    current = subprocess.run(['git', 'show', f'{revision}:{relative}'], cwd=project_root,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if current.returncode == 0:
        return current.stdout
    original = historical_project_path(project_root, relative)
    if original == relative:
        current.check_returncode()
    return subprocess.check_output(['git', 'show', f'{revision}:{original}'], cwd=project_root)


def resolve_source(project_root: Path, task_id: str, status: str, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if not path.is_relative_to(project_root):
        return path
    if status in {'IN_PROGRESS', 'IN_REVIEW'}:
        original_relative = historical_project_path(project_root, relative)
        mapping = project_root / 'agent/normalization-relocations.json'
        for entry in json.loads(mapping.read_text(encoding='utf-8'))['frozen_sources']:
            if entry['task_id'] != task_id or entry['old_project_path'] != original_relative:
                continue
            replacement = resolve_project_path(project_root, entry['new_project_path'])
            impact = resolve_project_path(project_root, entry['impact_path'])
            if (replacement.is_relative_to(project_root) and replacement.is_file()
                    and impact.is_relative_to(project_root) and impact.is_file()):
                return replacement
    return resolve_project_path(project_root, relative)
