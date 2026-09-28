"""Check the handoff, runtime field names and current dependency registration."""
import json
from pathlib import Path

from build_current import TASK, REPO, asset_drift, current_mapping
from generate_historical import asset_registry, UNITY_MANIFEST, G02_ASSET_LEDGER
from validate_historical import validate_asset_registry


def validate(data):
    expected = current_mapping()
    errors = []
    for key in expected:
        if data.get(key) != expected[key]:
            errors.append(key)
    if set(data) != set(expected):
        errors.append('fields')
    return errors


def main():
    data = json.loads((TASK / 'outputs/current-mapping.json').read_text(encoding='utf-8'))
    errors = validate(data)
    schema = json.loads((REPO / '02-技术研发/05-通信协议/contracts/runtime-contract-v2.2.schema.json').read_text(encoding='utf-8'))
    # The design's projection fields must exist in the actual F-05 telemetry definition.
    telemetry = schema['$defs']['telemetry_frame']['properties']
    for row in data['rows']:
        errors.extend(f'unknown runtime field:{field}' for field in row['source_fields'] if field not in telemetry)
    drift = json.loads((TASK / 'outputs/asset-drift.json').read_text(encoding='utf-8'))
    if drift != asset_drift():
        errors.append('current manifest drift report')
    manifest = json.loads(UNITY_MANIFEST.read_text(encoding='utf-8'))
    ledger = json.loads(G02_ASSET_LEDGER.read_text(encoding='utf-8'))
    validate_asset_registry(asset_registry(), manifest['dependencies'], set(ledger['groups']))
    if errors:
        print('\n'.join(f'ERROR: {error}' for error in errors))
        return 1
    print(f"PASS current V-03: mapping=40; runtime fields=v2.2; direct packages={len(manifest['dependencies'])}; fixed camera and fade separation; no license clearance")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
