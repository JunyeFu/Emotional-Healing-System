"""Historical acceptance and corrected synthetic behavior, not a real SAP."""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

import numpy as np
import pytest
from scipy import stats

TASK = Path(__file__).resolve().parents[1]
ROOT = TASK.parents[2]
resolve_path = runpy.run_path(str(ROOT / 'agent/tools/resolve_frozen_source.py'))['resolve_project_path']
GOV = ROOT / 'agent/governance/01-项目章程与规划/2026-08-05_SRP_IJHCI_全项目1-12步规划设计包_v1.0/24_团队任务与项目治理'
ARCHIVE = TASK / 'archive/signed-candidate'
SOURCES = json.loads((TASK / 'inputs/sources.json').read_text(encoding='utf-8'))
OLD = json.loads((ARCHIVE / 'evidence.json').read_text(encoding='utf-8'))
BUILD = runpy.run_path(str(TASK / 'execution/build_evidence.py'))
POWER = runpy.run_path(str(TASK / 'execution/power_simulation.py'))


@pytest.mark.parametrize('name,digest', list(SOURCES['archived_bytes'].items()))
def test_original_bytes(name, digest):
    assert hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest().upper() == digest


@pytest.mark.parametrize('entry', OLD['outputs'])
def test_original_core_identities_and_known_readme_drift(entry):
    matches = BUILD['text_hash'](ARCHIVE / entry['name']) == entry['sha256']
    assert matches is (entry['name'] != 'README.md')


@pytest.mark.parametrize('entry', OLD['sources'])
def test_original_source_identity(entry):
    raw = subprocess.check_output(['git', 'show', 'd701a4054a4a36030d37335efa65d67a93ed35c3:' + entry['name']], cwd=ROOT)
    text = raw.decode('utf-8-sig')
    normalized = '\n'.join(line.rstrip() for line in text.splitlines()) + '\n'
    assert hashlib.sha256(normalized.encode('utf-8')).hexdigest().upper() == entry['sha256_declared']


def test_original_acceptance_and_activity_contract_unchanged():
    acceptance = json.loads((GOV / 'u12_upgrade/acceptance/U12-04.json').read_text(encoding='utf-8'))
    assert acceptance['candidate_commit'] == 'd701a4054a4a36030d37335efa65d67a93ed35c3'
    assert acceptance['human_review']['reviewer'] == '傅钧烨'
    for field in ('human_review', 'independent_review'):
        report = resolve_path(ROOT, acceptance[field]['report_path'])
        raw = report.read_bytes().replace(b'\r\n', b'\n')
        assert hashlib.sha256(raw).hexdigest() == acceptance[field]['sha256_lf']
    assert (TASK / 'outputs/contract.json').read_bytes() == (ARCHIVE / 'contract.json').read_bytes()


def test_current_sap_corrects_completion_and_total_n():
    sap = (TASK / 'outputs/sap.md').read_text(encoding='utf-8')
    assert '不能自动替代主结果分析集' in sap
    assert '不是每臂48人' in sap
    assert '不保证保守' in sap and '不是正式MI' in sap
    spec = json.loads((TASK / 'outputs/power_spec.json').read_text(encoding='utf-8'))
    assert spec['analysis_sets_definition']['OBSERVED_CASE']['inclusion'] == 'observed_post_only'
    assert spec['data_generation']['baseline_coefficient'] == .5
    assert spec['grid']['effect_grid_residual_sd'] == list(POWER['DEFAULT_EFFECT_GRID'])


def test_hc3_and_residual_df_follow_actual_rows():
    cue = np.tile([0., 1.], 24)
    pre = np.random.default_rng(4).normal(size=48)
    strata = np.repeat([0., 1.], 24)
    matrix = np.column_stack([np.ones(48), cue, pre, strata])
    outcome = 3. - .3 * cue + .5 * pre + .1 * strata + np.random.default_rng(5).normal(size=48)
    keep = np.ones(48, dtype=bool)
    keep[[2, 4, 6, 8]] = False
    fit = POWER['_ols_hc3'](matrix[keep], outcome[keep])
    assert fit['df'] == 40.
    expected = 2 * stats.t.sf(abs(fit['beta'] / fit['se']), 40)
    assert POWER['_two_sided_p'](fit['beta'] / fit['se'], fit['df']) == pytest.approx(expected)


def test_cell_uses_each_actual_analysis_df(monkeypatch):
    cell = POWER['_cell_power']
    requested_df = []
    monkeypatch.setitem(cell.__globals__, '_replicate', lambda *args: {
        'PRIMARY_CONSERVATIVE': {'beta': -.4, 'se': .1, 'df': 44.},
        'OBSERVED_CASE': {'beta': -.4, 'se': .1, 'df': 40.}})
    def p_value(t, df):
        requested_df.append(df)
        return .04
    monkeypatch.setitem(cell.__globals__, '_two_sided_p', p_value)
    result = cell(1, 100, 48, .4)
    assert set(requested_df) == {40., 44.}
    assert result['OBSERVED_CASE']['mean_residual_df'] == 40.


@pytest.mark.parametrize('n', [47, 49, 0])
def test_no_silent_population_rounding(n):
    with pytest.raises(ValueError, match='TOTAL_N_REQUIRES_EVEN'):
        POWER['run_power_grid'](replications=100, n_grid=(n,), effect_grid=(0.,))


@pytest.mark.parametrize('effect', [-.4, 0., .4])
def test_direction_and_null_synthetic_scenarios(effect):
    result = POWER['run_power_grid'](seed=20260929, replications=100, n_grid=(48,), effect_grid=(effect,))
    assert result == POWER['run_power_grid'](seed=20260929, replications=100, n_grid=(48,), effect_grid=(effect,))
    assert result['effect_scale'] == 'RESIDUAL_SD_NOT_MARGINAL_COHENS_D'
    assert result['missing_policy_is_formal_mi'] is result['carried_forward_guaranteed_conservative'] is False
    if effect:
        assert np.sign(result['cells'][0]['OBSERVED_CASE']['mean_beta_estimate']) == -np.sign(effect)
    assert result['cells'][0]['OBSERVED_CASE']['mean_residual_df'] <= 44


def test_default_grid_rebuilds_current_output():
    actual = json.loads((TASK / 'outputs/power/power_grid.json').read_text(encoding='utf-8'))
    assert actual == POWER['run_power_grid']()
    assert len(actual['cells']) == 20
    assert all(cell[s]['valid_replications'] == 1000 for cell in actual['cells'] for s in POWER['ANALYSIS_SETS'])
    assert (TASK / 'outputs/power/power_report.md').read_text(encoding='utf-8') == POWER['render_power_report'](actual)


def test_cli_zero_and_output_exclusivity(tmp_path):
    destination = tmp_path / 'new-grid'
    command = [sys.executable, str(TASK / 'execution/power_simulation.py'), '--output-dir', str(destination),
               '--n-total', '48', '--effect-d', '0', '--replications', '100']
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads((destination / 'power_grid.json').read_text(encoding='utf-8'))
    assert result['effect_grid'] == [0.] and len(result['cells']) == 1
    original = (destination / 'power_grid.json').read_bytes()
    repeat = subprocess.run(command, capture_output=True, text=True)
    assert repeat.returncode != 0 and 'OUTPUT_DIRECTORY_EXISTS' in repeat.stderr
    assert (destination / 'power_grid.json').read_bytes() == original


def test_current_sources_and_evidence():
    assert all((ROOT / p).is_file() for p in SOURCES['paths'])
    assert json.loads((TASK / 'evidence/current-design.json').read_text(encoding='utf-8')) == BUILD['generate']()
    old_dir = GOV / 'u12_upgrade/U12-04_panas_sap'
    assert sorted(p.name for p in old_dir.iterdir() if p.is_file()) == ['README.md', 'U12-04独立复核记录.md']
