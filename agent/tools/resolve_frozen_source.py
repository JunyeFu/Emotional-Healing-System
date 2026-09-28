"""Locate explicitly migrated source originals without changing frozen input IDs."""
import json
from pathlib import Path


def resolve_source(project_root: Path, task_id: str, status: str, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if not path.is_relative_to(project_root) or path.is_file():
        return path
    if status not in {'IN_PROGRESS', 'IN_REVIEW'}:
        return path
    mapping = project_root / 'agent/normalization-relocations.json'
    for entry in json.loads(mapping.read_text(encoding='utf-8'))['frozen_sources']:
        if entry['task_id'] != task_id or entry['old_project_path'] != relative:
            continue
        replacement = (project_root / entry['new_project_path']).resolve()
        impact = (project_root / entry['impact_path']).resolve()
        if (replacement.is_relative_to(project_root) and replacement.is_file()
                and impact.is_relative_to(project_root) and impact.is_file()):
            return replacement
    return path
