# A-03-SPEC executable package

This package implements the scoring boundary and synthetic-only feasibility pipeline for the A-03-SPEC milestone.

## Public surface

- `score_panas`: scores configured positive and negative dimensions separately and requires a freeze receipt.
- `score_scci`: scores four ordinal items and labels the result as a manipulation check only.
- `score_comprehension`: scores eight binary items across four layers with explicit nonresponse handling.
- `score_effort`: scores the 1-9 mental-effort item with lower-is-less direction.
- `benjamini_hochberg`: applies FDR decisions to a named diagnostic item family.
- `evaluate_ordered_gate`: evaluates the non-compensatory Gate2 order after every formal parameter has a freeze entry.
- `run_simulation`: runs deterministic bounded Monte Carlo under two analysis sets.

Generate the candidate report from the repository root:

```powershell
$env:PYTHONPATH='02-技术研发/02-信号处理'
py -3.14 -m a03_gate2_spec.simulation `
  --output '00-项目管理/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/22_离线处理与科研分析/A-03_SPEC/synthetic_planning_anchor_report_v1.1.json' `
  --seed 20260906 `
  --replications 1000 `
  --per-condition 85 `
  --decision-scope existing_planning_anchor
```

The value 85 reuses the existing Gate1 planning anchor. The balanced complete-result target is 96 per condition; the recruitment cap of 240 is not a complete-result target. Every output is `SYNTHETIC_ONLY`; it cannot freeze formal margins, missing-data rules, sample size, or a Gate decision.
