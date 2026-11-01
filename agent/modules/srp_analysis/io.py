"""Existing bundle/privacy contracts at the external file boundary."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

MODULES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULES / 'data-governance'))
from srp_governance.privacy import privacy_lint_manifest
from srp_session_store.evidence_bundle import validate_bundle


def write_json(path, value):
    def clean(obj):
        if isinstance(obj, dict):
            return {str(k): clean(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [clean(v) for v in obj]
        if isinstance(obj, np.generic):
            return clean(obj.item())
        if isinstance(obj, float) and not np.isfinite(obj):
            return None
        return obj
    Path(path).write_text(json.dumps(clean(value), ensure_ascii=False, indent=2,
                                     allow_nan=False) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_input(base, reference):
    path = (base / reference).resolve()
    if base.resolve() not in path.parents or not path.is_file():
        raise ValueError('INPUT_MUST_BE_A_FILE_WITHIN_BUNDLE_ROOT')
    return path


def new_output(path, original_root):
    path, original_root = Path(path).resolve(), Path(original_root).resolve()
    if path == original_root or original_root in path.parents or path in original_root.parents:
        raise ValueError('OUTPUT_MUST_NOT_OVERLAP_INPUT_TREE')
    path.mkdir(parents=True, exist_ok=False)
    return path


def load_bundle(path):
    path = Path(path).resolve()
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    check = validate_bundle(value, path.parent)
    # Only absent materials may produce partial analysis; corrupt materials never do.
    missing_errors = ('MISSING_FAMILIES:', 'FAMILIES_WITHOUT_ARTIFACT:', 'REQUIRED_ARTIFACT_MISSING')
    hard_errors = [error for error in check['errors']
                   if not any(marker in error for marker in missing_errors)]
    if hard_errors:
        raise ValueError('BUNDLE_INVALID:' + ';'.join(hard_errors))
    by_id = {a['artifact_id']: a for a in value['artifacts']}
    def artifact(identifier, csv=False):
        item = by_id.get(identifier)
        if item is None or item['location_type'] != 'local_file':
            return pd.DataFrame() if csv else None
        source = safe_input(path.parent, item['location'])
        if not csv:
            return source
        frame = pd.read_csv(source, keep_default_na=True)
        privacy_lint_manifest({'rows': frame.fillna('').to_dict(orient='records')})
        return frame
    return path.parent, check, artifact


def save_frame(path, frame):
    frame.to_csv(path, index=False, encoding='utf-8', float_format='%.12g', lineterminator='\n')
