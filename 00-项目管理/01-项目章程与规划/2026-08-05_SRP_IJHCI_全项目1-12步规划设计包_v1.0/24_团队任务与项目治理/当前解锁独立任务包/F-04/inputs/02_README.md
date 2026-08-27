# F-04 Read-only Console

This directory is the F-04 W0 TouchDesigner shell. It is a local static
fixture demonstration, not a live device consumer and not a formal result.
Every page carries `READ ONLY / DEV-REPLAY / NOT LIVE`.

## Scope

- The fixture has five deterministic replay scenarios covering GOOD, DEGRADED,
  UNUSABLE, DISCONNECTED, and an out-of-order frame.
- The `telemetry` object is validated by the existing F-01 v2.1 reference
  validator and contains only its 29 contract-owned fields after filtering.
- `display_only` contains synthetic 25 Hz respiration, RR quality, cycle,
  logging status, and disabled request placeholders. It is never a wire frame.
- The UDP 5005 node is present only as a disabled `T-01 NOT ACTIVE` placeholder.
  Manual mark and abort are disabled `T-02 NOT ACTIVE` placeholders with no
  callback or request path.

## Build and verify

Run from the repository root:

```text
py -3.14 -m pytest 02-技术研发/03-TouchDesigner/f04_readonly_console/tests/test_f04_console.py -q
py -3.14 02-技术研发/03-TouchDesigner/f04_readonly_console/f04_node_plan.py
```

Open `F04_ReadonlyConsole.toe` in TouchDesigner 2025.32820. The reproducible
builder is `build_f04_touchdesigner.py`; execute it inside TouchDesigner after
the host artifacts have been generated. It replaces exactly
`/project1/F04_ReadonlyConsole`, writes the node inventory and error report,
and saves the `.tox`, `.toe`, and ten page screenshots.

## Evidence boundary

The screenshots prove page presence and visible read-only labeling only. The
synthetic waveform does not prove device acquisition, signal quality, the
interaction-state estimate, real-time 20 Hz consumption, request handling,
LIVE_E2E, scientific validity, or human acceptance. F-04 remains `IN_REVIEW`
until 傅钧烨 independently opens the `.toe`, switches all ten pages, checks
node permissions, and records PASS or FAIL.
