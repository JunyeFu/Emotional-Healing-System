# Codex Verification Log

> Use this template to record evidence for local project tasks. Add newest entries at the top.

## Template

### YYYY-MM-DD Task Name

| Field | Notes |
|---|---|
| Expected Observation | What should be true after the command, edit, test, screenshot, or inspection? |
| Actual Result | What actually happened? Include concise output or artifact paths. |
| Deviation / Surprise | What differed from expectation? If none, write `None`. |
| Verification Command | Command, test, screenshot path, or file check used. |
| Residual Risk | What remains uncertain or unverified? |

## Entries

### 2026-08-04 Confirm Separate Outcome And Process Models

| Field | Notes |
|---|---|
| Expected Observation | The Grill record assigns pre/post scale change to session-level sequence analysis and real-device records to segment-level composite-module process analysis, connects them without creating a synthetic total score, and does not claim an independently identified breathing-method effect. |
| Actual Result | Added U27, froze the outcome/process model boundary, required repeated-measures controls for segment analysis, retained device features as adaptive-policy inputs and explanatory evidence, and moved the next gate to selecting the exact standardized scale score. Updated the blackboard accordingly. |
| Deviation / Surprise | Existing project material mentions SAM, but the redesigned study has not established that SAM provides the intended unique short-term negative-emotion score. The instrument remains deliberately unfrozen. |
| Verification Command | Targeted `rg` checks for U27, both model levels, the no-synthetic-score rule, fixed-pair identification boundary, and the updated next gate; restricted-term scan; `git diff --check`; final `git status --short`. |
| Residual Risk | The exact scale, primary subscale, score direction, process feature family, missing-data rules, sample size, and statistical models remain unconfirmed. |

### 2026-08-04 Confirm Three-Stage Sequence Evidence Chain

| Field | Notes |
|---|---|
| Expected Observation | The Grill record distinguishes balanced random exploration, strategy learning, and independent confirmation; the first stage assigns all 24 complete sequences independently of real-time device data, while later adaptive selection remains separately testable. |
| Actual Result | Added U26, recorded pre-scale stratification with `1/24` sequence allocation, limited first-stage real-time device use to data capture and within-scene feedback, required policy freezing before independent confirmation, and retained balanced random assignment as the minimum comparison benchmark. Updated the blackboard to make the revised phase boundary current. |
| Deviation / Surprise | U24-U25 previously described state-constrained micro-random selection during exploration. U26 supersedes that first-stage mechanism but preserves adaptive selection for the independent confirmation stage. |
| Verification Command | Targeted `rg` checks for U26, `1/24`, all three phases, the supersession statement, policy freezing, and the next gate; restricted-term scan; `git diff --check`; final `git status --short`. |
| Residual Risk | The unique primary outcome, sample size, exact pre-scale strata, stage-three comparison conditions, policy form, and formal analysis model remain unconfirmed. |

### 2026-08-04 Confirm Micro-Randomized Adaptive Sequence Core

| Field | Notes |
|---|---|
| Expected Observation | The Grill record marks adaptive sequence generation and constrained random exploration as confirmed, explains why naive realized-sequence averages are biased, and leaves only the primary outcome definition as the next mainline gate. |
| Actual Result | Added U24-U25, froze the main paper direction as causal evaluation and explainable adaptive optimization of weather-breathing sequences, recorded nonzero random choice probabilities and required decision logs, and defined discovery, policy learning, and independent confirmation phases. Updated the blackboard to identify the primary outcome as the next gate. |
| Deviation / Surprise | The user wants both personalized real-time sequencing and estimates for all 24 complete sequences. Supporting both requires constrained exploration and propensity logging; a deterministic policy alone cannot identify all sequence effects. |
| Verification Command | Targeted `rg` checks for U24-U25, confirmed status, nonzero random probabilities, three research phases, working title, and next gate; restricted-term scan; `git diff --check`; final `git status --short`. |
| Residual Risk | The primary outcome, module pairings, randomization probabilities, quality constraints, sample simulation, and final comparison arms remain unconfirmed. |

### 2026-08-04 Confirm Ideal Output Portfolio

| Field | Notes |
|---|---|
| Expected Observation | The Grill record preserves all discussion after U16 and marks the user-confirmed ideal output portfolio as the current baseline without treating external acceptance or grants as guaranteed. |
| Actual Result | Appended U17-U23, covering fixed weather-breathing pairs, 24 sequence clarification, publication-quality assessment, three low-increment paper routes, real-device-only formal data, the distinction between ideal redesign and current evidence, and the confirmed output portfolio. Updated the blackboard so the next gate is selecting one primary paper contribution. |
| Deviation / Surprise | The later fixed-pair sequence direction supersedes the earlier independent 4×4 scene-breathing proposal. The main paper contribution remains unresolved among live-versus-replay, fixed sequence modeling, and explainable adaptive sequencing. |
| Verification Command | Targeted `rg` checks for U17-U23, confirmed output categories, superseded 4×4 status, real-device boundary, and the next gate; restricted-term scan; `git diff --check`; final `git status --short`. |
| Residual Risk | The portfolio is a target baseline. Journal acceptance, showcase acceptance, software registration completion, and patent grant depend on external review and cannot be guaranteed. |

### 2026-08-04 Grill Interview Context Preservation

| Field | Notes |
|---|---|
| Expected Observation | The project contains a dated, navigable record of the continuous Grill discussion, clearly separating original user inputs, confirmed decisions, superseded ideas, evidence-based rationale, pending recommendations, open questions, and the next interview gate. |
| Actual Result | Added `00-项目管理/看板与进度/2026-08-04_Grill访谈原始总结与决策演化.md`; linked it from the M00 README; updated the project-local blackboard. The record preserves the evolution from module boundaries through Unity/TD separation, passive four-scene flow, overall outcome evidence, and the proposed 4×4 scene-breathing match design. |
| Deviation / Surprise | The current module map still describes TD Spout as a Unity input, while the later confirmed target makes Unity independent of TD. This discrepancy is recorded for a future architecture update after the research mainline is confirmed, not changed in this preservation task. |
| Verification Command | Targeted `rg` checks for required decisions, decision-state labels, restricted terms, and the M00 navigation link; Markdown relative-link check; `git diff --check`; final `git status --short`. |
| Residual Risk | Assistant replies before the latest turn are preserved as decision summaries rather than a byte-for-byte transcript. The proposed 4×4 design, scene-level verbal ratings, comparison condition, and four standardized breathing conditions remain unconfirmed. |

### 2026-08-04 Project Module Reorganization

| Field | Notes |
|---|---|
| Expected Observation | The D-drive repository has one authoritative module map, stable entry pages for each top-level module group, no active references to the old C-drive path or user-deleted evidence files, and unchanged Python behavior. |
| Actual Result | Added `PROJECT_MODULES.md` with M00-M10 responsibilities, interfaces, dependencies, placement rules, and validation entry points. Added entry pages for project management, experience design, verification evidence, and delivery. Updated root, development, runbook, board, and workflow navigation. Python tests passed: 42 passed. |
| Deviation / Surprise | The worktree also contained a user modification to `CLAUDE.md`, an untracked `SRP/` asset directory, and a root docx duplicate. The duplicate docx hash matches the copy under project management; all of these pre-existing changes were preserved and excluded from this task. |
| Verification Command | `py -3.14 -m pytest '02-技术研发/01-数据采集/tests' '02-技术研发/02-信号处理/tests' '02-技术研发/05-通信协议/tests' '02-技术研发/tests' -q`; targeted `rg` scans for old paths, deleted entries, and restricted terms; relative Markdown link check; `git diff --check`. |
| Residual Risk | TD, Spout, and Unity Play Mode were not launched in this documentation-only task. User-deleted verification materials remain absent, so module M08 records structure and evidence requirements but not a completed full-system verification. |

### 2026-07-01 Project File and Document Cleanup

| Field | Notes |
|---|---|
| Expected Observation | Outdated entry docs are updated, ignored temporary artifacts are removed, authoritative protocol references point to `UDP字段冻结_v1.2.md`, and Python tests still pass. |
| Actual Result | Updated AGENTS, CLAUDE, README, current board, development plan, UDP docs, TD bridge comment, cleanup record, data README, and blackboard. Removed caches, old zip backups, mock CSV, duplicate reference zip, and garbled Unity/MCP runtime mirror. Python 3.14.4 tests passed: 42 passed. |
| Deviation / Surprise | The previous `.hermes-venv` interpreter no longer exists; `py -3.14` is the current valid Python entry. |
| Verification Command | `py -3.14 -m pytest '02-技术研发/01-数据采集/tests' '02-技术研发/02-信号处理/tests' '02-技术研发/05-通信协议/tests' '02-技术研发/tests' -q`; `rg` consistency scans; `git diff --check`; targeted `Test-Path` checks for removed artifacts. |
| Residual Risk | Unity generated cache directories remain intentionally preserved to avoid slow reimport; stage 6/7 evidence materials still need to be populated under `04-成果与交付/`. |

### 2026-06-24 Enable SAPIEN-Lite Workflow

| Field | Notes |
|---|---|
| Expected Observation | `AGENTS.md` contains an appended `Codex Workflow` section; `work/` contains blackboard, verification log, and evaluation harness templates. |
| Actual Result | All three workflow files exist; `AGENTS.md` contains `Codex Workflow`; templates contain the required blackboard, verification, and 30-task harness sections. |
| Deviation / Surprise | `git diff --stat` only showed tracked files before staging; untracked `work/` files are expected to appear in `git status`. |
| Verification Command | `Test-Path work/codex-blackboard.md`; `Test-Path work/codex-verification-log.md`; `Test-Path work/codex-evaluation-harness.md`; `rg -n "Codex Workflow|Current Task Goal|Expected Observation|30-Task Log|High-Risk Action Intercepted" AGENTS.md work` |
| Residual Risk | Workflow quality depends on future tasks consistently updating the blackboard and verification log. |
